import { useState, useRef, useEffect } from "react";
import {
  Box,
  Flex,
  Text,
  Textarea,
  Button,
  VStack,
  HStack,
  IconButton,
} from "@chakra-ui/react";
import { useNavigate } from "react-router-dom";
import { sendChatMessage, getChatHistory, downloadArtifact, logout, uploadDocument, getConversations, createConversation, deleteConversation } from "../api.js";
import MessageBubble from "../components/MessageBubble.jsx";
import Sidebar from "../components/Sidebar.jsx";
import LeftSidebar from "../components/LeftSidebar.jsx";

export default function Chat() {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [state, setState] = useState({});
  const [error, setError] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const scrollRef = useRef(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    async function init() {
      try {
        let convs = await getConversations();
        if (convs.length === 0) {
          const newConv = await createConversation();
          convs = [newConv];
        }
        setConversations(convs);
        setActiveConversationId(convs[0].id);
      } catch (err) {
        setError(err.message);
        if (err.message.includes("Session expired")) {
          navigate("/login");
        }
      }
    }
    init();
  }, [navigate]);

  useEffect(() => {
    if (!activeConversationId) return;

    async function loadHistory() {
      setLoadingHistory(true);
      try {
        const data = await getChatHistory(activeConversationId);
        if (data.messages?.length) {
          setMessages([...data.messages]);
        } else {
          setMessages([
            {
              role: "assistant",
              content:
                "Tell me about a project or research idea you're working on, and I can help with literature gaps, a technical plan, a teaching plan and course, lab exercises, or experiment design.",
            },
          ]);
        }
        setState(data.state || {});
      } catch (err) {
        setError(err.message);
        if (err.message.includes("Session expired")) {
          navigate("/login");
        }
      } finally {
        setLoadingHistory(false);
      }
    }

    loadHistory();
  }, [activeConversationId, navigate]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending || loadingHistory || !activeConversationId) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSending(true);
    setError("");

    try {
      const data = await sendChatMessage(text, activeConversationId);
      
      if (data.title) {
        setConversations(prev => prev.map(c => c.id === activeConversationId ? { ...c, title: data.title } : c));
      }
      
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
        },
      ]);
      setState(data.state || {});
    } catch (err) {
      setError(err.message);
      if (err.message.includes("Session expired")) {
        navigate("/login");
      }
    } finally {
      setSending(false);
    }
  }

  async function handleNewChat() {
    try {
      const newConv = await createConversation();
      setConversations([newConv, ...conversations]);
      setActiveConversationId(newConv.id);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteChat(id) {
    try {
      await deleteConversation(id);
      const newConvs = conversations.filter(c => c.id !== id);
      setConversations(newConvs);
      if (activeConversationId === id) {
        if (newConvs.length > 0) {
          setActiveConversationId(newConvs[0].id);
        } else {
          handleNewChat();
        }
      }
    } catch (err) {
      setError(err.message);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setError("");
    
    try {
      const res = await uploadDocument(file, activeConversationId);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `✅ File "${file.name}" uploaded successfully. You can now ask questions about it.`,
        },
      ]);
    } catch (err) {
      setError(err.message);
      if (err.message.includes("Session expired")) {
        navigate("/login");
      }
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <Flex h="100vh" bg="paper.100">
      <LeftSidebar 
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={setActiveConversationId}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
      />

      <Flex direction="column" flex="1" minW="0">
        {/* Header */}
        <Flex
          align="center"
          justify="space-between"
          px={6}
          py={4}
          borderBottom="1px solid"
          borderColor="paper.300"
        >
          <HStack spacing={3}>
            <Text fontFamily="mono" fontSize="xs" color="slate.500" letterSpacing="wide">
              [ CONSILIAI ]
            </Text>
            <Text fontSize="sm" color="ink.500">
              Research-to-education transfer assistant
            </Text>
          </HStack>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            Sign out
          </Button>
        </Flex>

        {/* Messages */}
        <VStack
          flex="1"
          overflowY="auto"
          align="stretch"
          spacing={4}
          px={6}
          py={6}
        >
          {messages.map((m, i) => (
            <Flex key={i} justify={m.role === "user" ? "flex-end" : "flex-start"}>
              <MessageBubble
                role={m.role}
                content={m.content}
                downloads={m.downloads}
                onDownload={downloadArtifact}
              />
            </Flex>
          ))}
          {sending && (
            <Flex justify="flex-start">
              <Box
                bg="paper.50"
                border="1px solid"
                borderColor="paper.300"
                borderRadius="lg"
                px={4}
                py={3}
              >
                <Text fontSize="sm" color="ink.500" fontStyle="italic">
                  Thinking…
                </Text>
              </Box>
            </Flex>
          )}
          <div ref={scrollRef} />
        </VStack>

        {error && (
          <Box px={6} pb={2}>
            <Text fontSize="sm" color="red.500">
              {error}
            </Text>
          </Box>
        )}

        {/* Input */}
        <Flex px={6} py={4} borderTop="1px solid" borderColor="paper.300" gap={3}>
          <input 
            type="file" 
            hidden 
            ref={fileInputRef} 
            onChange={handleFileUpload}
            accept="application/pdf"
          />
          <Button 
            onClick={() => fileInputRef.current?.click()} 
            isLoading={uploading} 
            px={4}
            variant="outline"
            title="Upload personal document"
          >
            📎
          </Button>
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe an idea, or ask a question…"
            resize="none"
            rows={1}
            bg="paper.50"
          />
          <Button onClick={handleSend} isLoading={sending} px={6}>
            Send
          </Button>
        </Flex>
      </Flex>

      <Sidebar state={state} />
    </Flex>
  );
}
