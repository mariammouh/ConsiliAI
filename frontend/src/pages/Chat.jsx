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
import { sendChatMessage, getChatHistory, downloadArtifact, logout, uploadDocument } from "../api.js";
import MessageBubble from "../components/MessageBubble.jsx";
import Sidebar from "../components/Sidebar.jsx";

export default function Chat() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Tell me about a project or research idea you're working on, and I can help with literature gaps, a technical plan, a teaching plan and course, lab exercises, or experiment design.",
    },
  ]);
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
    async function loadHistory() {
      try {
        const data = await getChatHistory();
        if (data.messages?.length) {
          const restoredMessages = [...data.messages];
          const lastMessage = restoredMessages[restoredMessages.length - 1];
          if (lastMessage?.role === "assistant") {
            lastMessage.downloads = [
              ...(data.course_downloads || []),
              ...(data.lab_downloads || []),
            ];
          }
          setMessages(restoredMessages);
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
  }, [navigate]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending || loadingHistory) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSending(true);
    setError("");

    try {
      const data = await sendChatMessage(text);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
          downloads: [
            ...(data.course_downloads || []),
            ...(data.lab_downloads || []),
          ],
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
      const res = await uploadDocument(file);
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
