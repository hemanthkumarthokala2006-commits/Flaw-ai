import React, { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { systemAPI, chatAPI } from '../../services/api';
import './VoiceAssistant.css';

export default function VoiceAssistant({ onClose, chatId, onNewMessage }) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [status, setStatus] = useState('Initializing...');
  
  const recognitionRef = useRef(null);
  const utteranceRef = useRef(null);
  const isSpeakingRef = useRef(false);
  const isListeningRef = useRef(false);

  const [volume, setVolume] = useState(0);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    // 1. Setup Audio Visualizer (to check if mic is even working)
    const setupAudio = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        streamRef.current = stream;
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        audioContextRef.current = audioContext;
        const analyser = audioContext.createAnalyser();
        analyserRef.current = analyser;
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;
        
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const updateVolume = () => {
          if (!analyserRef.current) return;
          analyserRef.current.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
          }
          const average = sum / bufferLength;
          setVolume(average);
          requestAnimationFrame(updateVolume);
        };
        updateVolume();
      } catch (err) {
        console.error("Audio capture failed", err);
        setStatus("Error: Microphone access denied by system.");
      }
    };
    setupAudio();

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onstart = () => {
        isListeningRef.current = true;
        setIsListening(true);
        setStatus('Listening...');
      };

      recognitionRef.current.onresult = (event) => {
        const current = event.resultIndex;
        const result = event.results[current];
        const transcriptText = result[0].transcript;
        setTranscript(transcriptText);

        if (result.isFinal) {
          handleCommand(transcriptText.toLowerCase());
        }
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error', event.error);
        isListeningRef.current = false;
        setIsListening(false);
        if (event.error === 'no-speech' || event.error === 'network' || event.error === 'not-allowed') {
          // Ignore no-speech and let onend handle the restart if not speaking
        } else {
          setStatus('Error: ' + event.error);
        }
      };

      recognitionRef.current.onend = () => {
        isListeningRef.current = false;
        setIsListening(false);
        
        // Auto-restart if we are not currently speaking and not closed
        if (!isSpeakingRef.current) {
          console.log("Mic ended, restarting...");
          setTimeout(() => {
            if (!isSpeakingRef.current) startListening();
          }, 100);
        }
      };

      startListening();
    } else {
      setStatus('Speech recognition not supported in this browser.');
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.onend = null; // Prevent restart on unmount
        recognitionRef.current.stop();
      }
      window.speechSynthesis.cancel();
    };
  }, []);

  const startListening = () => {
    if (recognitionRef.current && !isListeningRef.current && !isSpeakingRef.current) {
      try {
        recognitionRef.current.start();
      } catch (error) {
        console.error('Failed to start recognition', error);
      }
    }
  };

  const speak = (text, callback) => {
    if (recognitionRef.current) recognitionRef.current.stop();
    
    isSpeakingRef.current = true;
    setIsSpeaking(true);
    setStatus('Speaking...');
    
    utteranceRef.current = new SpeechSynthesisUtterance(text);
    
    const voices = window.speechSynthesis.getVoices();
    const femaleVoice = voices.find(v => v.name.includes('Female') || v.name.includes('Zira') || v.name.includes('Google UK English Female'));
    if (femaleVoice) utteranceRef.current.voice = femaleVoice;
    
    utteranceRef.current.pitch = 1.2;
    utteranceRef.current.rate = 1.0;
    
    utteranceRef.current.onend = () => {
      isSpeakingRef.current = false;
      setIsSpeaking(false);
      setStatus('Listening...');
      setTranscript('');
      if (callback) callback();
      setTimeout(() => startListening(), 500);
    };
    
    // Fallback in case onend doesn't fire (browser bug)
    setTimeout(() => {
      if (isSpeakingRef.current) {
        isSpeakingRef.current = false;
        setIsSpeaking(false);
        setStatus('Listening...');
        setTimeout(() => startListening(), 500);
      }
    }, text.length * 100 + 2000);

    window.speechSynthesis.speak(utteranceRef.current);
  };

  const handleCommand = async (command) => {
    isListeningRef.current = false;
    setIsListening(false);
    setStatus('Processing...');

    const lowerCmd = command.trim();

    // 1. FAST PATHS (Local commands)
    if (lowerCmd.includes('close') || lowerCmd.includes('exit') || lowerCmd.includes('stop')) {
      speak('Goodbye!', onClose);
      return;
    }

    if (lowerCmd.includes('time')) {
      const time = new Date().toLocaleTimeString();
      speak(`The current time is ${time}.`);
      return;
    }

    // 2. SMART INTENT PROCESSING (via Gemini)
    try {
      const result = await systemAPI.process(command);
      
      if (result.status === "success") {
        const { intent, params } = result;

        switch (intent) {
          case "open_app":
            speak(`Opening ${params.app_name} on your device.`);
            try {
              await systemAPI.openApp(params.app_name);
            } catch (e) {
              window.open(`https://www.${params.app_name.replace(/\s+/g, '')}.com`, '_blank');
            }
            break;

          case "play_media":
            speak(`Playing ${params.query} on YouTube`);
            try {
              await systemAPI.playMedia(params.query);
            } catch (e) {
              window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(params.query)}`, '_blank');
            }
            break;

          case "send_message":
            if (params.person) {
              speak(`Sending your ${params.is_image ? 'image' : 'message'}.`);
              try {
                await systemAPI.sendMessage(params.person, params.message || "Hello", params.is_image);
              } catch (e) {
                const text = encodeURIComponent(params.is_image ? '' : `Hey ${params.person}, ${params.message}`);
                window.open(`https://api.whatsapp.com/send?text=${text}`, '_blank');
              }
            } else {
              speak('Who would you like me to send it to?');
            }
            break;

          case "take_screenshot":
            speak("Taking a screenshot.");
            try {
              const ssRes = await systemAPI.takeScreenshot();
              if (ssRes.media_url) {
                if (chatId && onNewMessage) {
                  // Post screenshot to chat
                  const userMsg = { id: Date.now(), role: "user", content: params.prompt || "Analyze this screenshot", message_type: "text", created_at: new Date().toISOString() };
                  onNewMessage(userMsg);
                  
                  // Trigger AI response with screenshot
                  const aiMsg = await chatAPI.sendMessage(chatId, params.prompt || "What is in this screenshot?", "text", ssRes.media_url);
                  onNewMessage(aiMsg);
                  speak(aiMsg.content);
                } else {
                  // Fallback if no chat active
                  if (params.prompt) {
                    const aiResp = await systemAPI.askAgent(`${params.prompt} (referring to the screenshot I just took)`, ssRes.media_url);
                    speak(aiResp.answer);
                  } else {
                    speak("Screenshot captured.");
                  }
                }
              }
            } catch (e) {
              console.error(e);
              speak("I failed to take a screenshot.");
            }
            break;

          case "search_web":
            speak(`Searching the web for ${params.query}`, () => {
              window.open(`https://www.google.com/search?q=${encodeURIComponent(params.query)}`, '_blank');
            });
            break;

          case "chat":
          default:
            if (params.response) {
              speak(params.response);
            } else {
              const legacyResp = await systemAPI.askAgent(command);
              speak(legacyResp.answer);
            }
            break;
        }
      } else {
        throw new Error("Processing failed");
      }
    } catch (e) {
      console.error("Smart processing failed, falling back to web search", e);
      speak(`Let me search the web for ${command}`, () => {
        window.open(`https://www.google.com/search?q=${encodeURIComponent(command)}`, '_blank');
      });
    }
  };

  return (
    <div className="voice-assistant-overlay fade-in">
      <button className="close-btn" onClick={onClose} title="Close">
        <X size={28} />
      </button>

      <div className={`character-container ${isListening ? 'listening' : ''}`}>
        {isListening && <div className="sound-waves"></div>}
        <div className={`anime-character ${isSpeaking ? 'speaking' : ''}`}>
          {/* ... existing character parts ... */}
          <div className="hair-front"></div>
          <div className="eyes">
            <div className="eye"><div className="pupil"></div></div>
            <div className="eye"><div className="pupil"></div></div>
          </div>
          <div className="blush">
            <div className="blush-mark"></div>
            <div className="blush-mark"></div>
          </div>
          <div className="mouth"></div>
        </div>
      </div>

      <div className="volume-meter-container" style={{ width: '200px', height: '10px', background: '#333', borderRadius: '5px', overflow: 'hidden', margin: '20px auto' }}>
        <div className="volume-bar" style={{ width: `${volume}%`, height: '100%', background: volume > 30 ? '#00f2fe' : '#444', transition: 'width 0.1s ease' }}></div>
      </div>

      <div className="status-text">{status}</div>
      {status.includes('Error') && (
        <div style={{ color: '#ff4d4d', fontSize: '14px', marginTop: '5px' }}>
          Please check if your mic is allowed in browser settings.
        </div>
      )}
      <div className="transcript">{transcript || (isListening ? "Listening..." : "")}</div>
    </div>
  );
}
