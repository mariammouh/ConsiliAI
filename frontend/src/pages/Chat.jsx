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
  Tooltip,
  useColorModeValue,
} from "@chakra-ui/react";
import { useNavigate } from "react-router-dom";
import { FiChevronLeft, FiChevronRight, FiPaperclip } from "react-icons/fi";
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

  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false);
  const [isRightCollapsed, setIsRightCollapsed] = useState(false);
  const [density, setDensity] = useState(() => localStorage.getItem("consiliai_density") || "comfortable");

  const scrollRef = useRef(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const bgMain = useColorModeValue("paper.50", "gray.900");
  const bgFloatingBtn = useColorModeValue("paper.100", "gray.800");
  const colorFloatingBtn = useColorModeValue("ink.700", "gray.200");
  const borderColorFloatingBtn = useColorModeValue("paper.300", "gray.700");
  const bgInputArea = useColorModeValue("paper.50", "gray.800");
  const textColorInput = useColorModeValue("ink.900", "gray.100");

  const handleDensityChange = (newDensity) => {
    setDensity(newDensity);
    localStorage.setItem("consiliai_density", newDensity);
  };

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
          content: `File "${file.name}" uploaded successfully. You can now ask questions about it.`,
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
    <Flex h="100vh" bg={bgMain}>
      <LeftSidebar 
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={setActiveConversationId}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        onLogout={handleLogout}
        state={state}
        messages={messages}
        isCollapsed={isLeftCollapsed}
        onToggleCollapse={() => setIsLeftCollapsed(!isLeftCollapsed)}
        density={density}
        onDensityChange={handleDensityChange}
      />

      <Flex direction="column" flex="1" minW="0" position="relative">
        {/* Floating expand buttons when sidebars are collapsed */}
        {isLeftCollapsed && (
          <Tooltip label="Expand left sidebar" placement="right">
            <IconButton
              icon={<FiChevronRight />}
              aria-label="Expand left sidebar"
              size="sm"
              variant="solid"
              bg={bgFloatingBtn}
              color={colorFloatingBtn}
              boxShadow="0px 2px 8px rgba(30,25,17,0.12)"
              border="1px solid"
              borderColor={borderColorFloatingBtn}
              _hover={{ bg: bgFloatingBtn }}
              position="absolute"
              top="16px"
              left="16px"
              zIndex={20}
              onClick={() => setIsLeftCollapsed(false)}
            />
          </Tooltip>
        )}

        {isRightCollapsed && (
          <Tooltip label="Expand right sidebar" placement="left">
            <IconButton
              icon={<FiChevronLeft />}
              aria-label="Expand right sidebar"
              size="sm"
              variant="solid"
              bg={bgFloatingBtn}
              color={colorFloatingBtn}
              boxShadow="0px 2px 8px rgba(30,25,17,0.12)"
              border="1px solid"
              borderColor={borderColorFloatingBtn}
              _hover={{ bg: bgFloatingBtn }}
              position="absolute"
              top="16px"
              right="16px"
              zIndex={20}
              onClick={() => setIsRightCollapsed(false)}
            />
          </Tooltip>
        )}

        {/* Messages */}
        <VStack
          flex="1"
          overflowY="auto"
          align="stretch"
          spacing={density === "compact" ? 2 : 4}
          px={density === "compact" ? 4 : 6}
          py={density === "compact" ? 3 : 6}
        >
          {messages.map((m, i) => (
            <Flex key={i} justify={m.role === "user" ? "flex-end" : "flex-start"}>
              <MessageBubble
                role={m.role}
                bg="paper.50"
                content={m.content}
                downloads={m.downloads}
                onDownload={downloadArtifact}
                density={density}
              />
            </Flex>
          ))}
          {sending && (
            <Flex justify="flex-start">
              <Box bg={bgFloatingBtn} borderRadius="18px" borderBottomLeftRadius="4px" px={4} py={3}>
                <Text fontSize="sm" color={colorFloatingBtn} fontStyle="italic">
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
        <Flex px={6} py={4} gap={3} boxShadow="0px -1px 0px rgba(30,25,17,0.06)">
          <input 
            type="file" 
            hidden 
            ref={fileInputRef} 
            onChange={handleFileUpload}
            accept="application/pdf"
          />
          <IconButton 
            icon={<FiPaperclip />}
            aria-label="Upload personal document"
            onClick={() => fileInputRef.current?.click()} 
            isLoading={uploading} 
            variant="outline"
          />
          <Textarea 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe an idea, or ask a question…" 
            resize="none" 
            rows={1} 
            bg={bgInputArea} 
            color={textColorInput}
            borderRadius="14px" 
            border="none"
            boxShadow="inset 0 0 0 1px var(--chakra-colors-paper-300)" 
          />
          <Button 
            onClick={handleSend} 
            isLoading={sending} 
            px={6} 
            borderRadius="14px"
            boxShadow="0px 4px 10px rgba(193,90,54,0.28)"
          >
            Send
          </Button>
        </Flex>
      </Flex>

      <Sidebar 
        state={state} 
        isCollapsed={isRightCollapsed}
        onToggleCollapse={() => setIsRightCollapsed(!isRightCollapsed)}
      />
    </Flex>
  );
}


