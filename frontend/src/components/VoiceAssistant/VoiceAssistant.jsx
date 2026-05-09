import React, { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { systemAPI } from '../../services/api';
import './VoiceAssistant.css';

export default function VoiceAssistant({ onClose }) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [status, setStatus] = useState('Initializing...');
  
  const recognitionRef = useRef(null);
  const utteranceRef = useRef(null);
  const isSpeakingRef = useRef(false);
  const isListeningRef = useRef(false);

  useEffect(() => {
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
          setTimeout(() => {
            startListening();
          }, 300);
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

    // 4. SEND MESSAGE COMMAND
    const msgMatch = lowerCmd.match(/\bsend\s+(?:a\s+)?(?:message|text|image|whatsapp|pic|picture)\s+to\s+(.+?)(?:\s+(?:saying|that|with|about)\s+(.+))?$/i);
    if (msgMatch || lowerCmd.startsWith('message ')) {
      let person = "";
      let content = "Hello";
      if (msgMatch) {
        person = msgMatch[1].trim();
        content = msgMatch[2] ? msgMatch[2].trim() : "Hello";
      } else {
        const msgParts = lowerCmd.match(/^message\s+(.+?)(?:\s+(?:saying|that)\s+(.+))?$/i);
        person = msgParts?.[1]?.trim() || "";
        content = msgParts?.[2]?.trim() || "Hello";
      }

      if (person) {
        speak(`Opening WhatsApp to send your message to ${person}.`, () => {
          // api.whatsapp.com is 100% reliable and links directly to desktop or web app
          const text = encodeURIComponent(`Hey ${person.charAt(0).toUpperCase() + person.slice(1)}, ${content}`);
          window.open(`https://api.whatsapp.com/send?text=${text}`, '_blank');
        });
      } else {
        speak('Who would you like me to send a message to?');
      }
      return;
    }

    // 3. PLAY COMMAND
    const playMatch = lowerCmd.match(/\b(?:play)\s+(.+)/i) || lowerCmd.match(/\bopen\s+(.+?\s+(?:songs?|music|movies?|videos?|trailers?))/i);
    if (playMatch) {
      const query = playMatch[1].trim();
      try {
        await systemAPI.playMedia(query);
        speak(`Playing ${query} on YouTube`);
      } catch (e) {
        console.log("Local play failed, falling back to web:", e);
        speak(`Playing ${query} on YouTube`, () => {
          window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`, '_blank');
        });
      }
      return;
    }

    // 1. OPEN COMMAND
    const openMatch = lowerCmd.match(/\bopen\s+([a-z0-9\s]+)/i);
    if (openMatch) {
      const target = openMatch[1].trim();
      try {
        await systemAPI.openApp(target);
        speak(`Opening ${target} on your device.`);
      } catch (e) {
        console.log("Local open failed, falling back to web:", e);
        speak(`Opening ${target}`, () => {
          const domain = target.replace(/\s+/g, '');
          window.open(`https://www.${domain}.com`, '_blank');
        });
      }
      return;
    }

    // 2. SEARCH COMMAND
    const searchMatch = lowerCmd.match(/\bsearch\s+(?:for\s+)?(.+)/i);
    if (searchMatch) {
      const query = searchMatch[1].trim();
      speak(`Searching the web for ${query}`, () => {
        window.open(`https://www.google.com/search?q=${encodeURIComponent(query)}`, '_blank');
      });
      return;
    }

    // 5. BASIC CONVERSATION
    if (lowerCmd.includes('hello') || lowerCmd.includes('hi flaw')) {
      speak('Hello! I am your AI assistant. How can I help you today?');
      return;
    }

    if (lowerCmd.includes('close') || lowerCmd.includes('exit') || lowerCmd.includes('stop')) {
      speak('Goodbye!', onClose);
      return;
    }

    if (lowerCmd.includes('time')) {
      const time = new Date().toLocaleTimeString();
      speak(`The current time is ${time}.`);
      return;
    }

    // 6. DEFAULT FALLBACK
    speak(`Let me search the web for ${command}`, () => {
      window.open(`https://www.google.com/search?q=${encodeURIComponent(command)}`, '_blank');
    });
  };

  return (
    <div className="voice-assistant-overlay fade-in">
      <button className="close-btn" onClick={onClose} title="Close">
        <X size={28} />
      </button>

      <div className={`character-container ${isListening ? 'listening' : ''}`}>
        {isListening && <div className="sound-waves"></div>}
        <div className={`anime-character ${isSpeaking ? 'speaking' : ''}`}>
          <div className="eyes">
            <div className="eye"></div>
            <div className="eye"></div>
          </div>
          <div className="mouth"></div>
        </div>
      </div>

      <div className="status-text">{status}</div>
      <div className="transcript">{transcript}</div>
    </div>
  );
}
