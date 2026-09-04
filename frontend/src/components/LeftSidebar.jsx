import { useState, useEffect } from "react";
import {
  Box,
  Text,
  VStack,
  HStack,
  Button,
  IconButton,
  Image,
  Tooltip,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Badge,
  RadioGroup,
  Radio,
  Stack,
  Input,
  Select,
  useDisclosure,
  useColorMode,
  useColorModeValue,
  useToast,
} from "@chakra-ui/react";
import { 
  FiChevronLeft, 
  FiUser, 
  FiDownload, 
  FiSliders, 
  FiTrash2, 
  FiFileText, 
  FiCode, 
  FiSettings, 
  FiX, 
  FiSun, 
  FiMoon,
  FiCpu,
  FiAlertTriangle
} from "react-icons/fi";
import { getUserMe, getSettings, updateSettings, downloadProjectZip, deleteAllUserData } from "../api.js";


export default function LeftSidebar({ 
  conversations, 
  activeConversationId, 
  onSelectConversation, 
  onNewChat, 
  onDeleteChat,
  onLogout,
  onDeleteAllData,
  state = {},
  messages = [],
  isCollapsed = false,
  onToggleCollapse,
  density = "comfortable",
  onDensityChange
}) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { colorMode, setColorMode } = useColorMode();
  const toast = useToast();
  const [sidebarWidth, setSidebarWidth] = useState(250);
  const [isResizing, setIsResizing] = useState(false);
  const [userData, setUserData] = useState(null);
  const [llmProvider, setLlmProvider] = useState("cloud");
  const [isUpdatingProvider, setIsUpdatingProvider] = useState(false);

  // Chat deletion confirmation modal state
  const [chatToDelete, setChatToDelete] = useState(null);

  // Delete all user data confirmation modal state
  const [isDeleteAllModalOpen, setIsDeleteAllModalOpen] = useState(false);
  const [deleteAllConfirmText, setDeleteAllConfirmText] = useState("");
  const [isDeletingAll, setIsDeletingAll] = useState(false);

  // Project download state
  const [selectedExportProject, setSelectedExportProject] = useState("");
  const [isDownloadingProject, setIsDownloadingProject] = useState(false);

  useEffect(() => {
    if (activeConversationId) {
      setSelectedExportProject(activeConversationId);
    } else if (conversations?.length > 0) {
      setSelectedExportProject(conversations[0].id);
    }
  }, [activeConversationId, conversations]);


  const bgSidebar = useColorModeValue("paper.50", "gray.900");
  const borderColor = useColorModeValue("paper.300", "gray.700");
  const bgCard = useColorModeValue("paper.100", "gray.800");
  const bgHover = useColorModeValue("paper.100", "gray.700");
  const textPrimary = useColorModeValue("ink.900", "gray.100");
  const textSecondary = useColorModeValue("ink.600", "gray.400");
  const textSubtle = useColorModeValue("slate.500", "gray.400");

  const SECTION_CARD = {
    bg: "white",
    borderRadius: "card",
    border: "1px solid",
    borderColor: "paper.300",
    boxShadow: "soft",
  };

  const SECTION_CARD_SUBTLE = {
    bg: "paper.50",
    borderRadius: "control",
    border: "1px solid",
    borderColor: "paper.300",
  };

  useEffect(() => {
    if (isOpen) {
      getUserMe().then((data) => {
        if (data) setUserData(data);
      });
      getSettings()
        .then((s) => {
          if (s?.llm_provider) setLlmProvider(s.llm_provider);
        })
        .catch(() => {});
    }
  }, [isOpen]);

  const handleProviderChange = async (val) => {
    setLlmProvider(val);
    setIsUpdatingProvider(true);
    try {
      await updateSettings({ llm_provider: val });
      toast({
        title: "Model preference saved",
        description: `Active LLM provider set to ${val === "cloud" ? "Cloud (Groq + Gemini)" : "Local (Ollama)"}`,
        status: "success",
        duration: 3000,
        isClosable: true,
      });
    } catch (err) {
      toast({
        title: "Failed to update preference",
        description: err.message,
        status: "error",
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setIsUpdatingProvider(false);
    }
  };


  const handleDensityChange = (newDensity) => {
    if (onDensityChange) {
      onDensityChange(newDensity);
    }
  };

  const handleExportMarkdown = () => {
    let content = `# ConsiliAI Research Export\n\n`;
    if (state.idea) content += `## Research Idea\n${state.idea}\n\n`;
    if (state.papers?.length) {
      content += `## Literature (${state.papers.length} papers)\n`;
      state.papers.forEach((p, i) => {
        content += `${i + 1}. **${p.title}** - ${p.url || p.source || "N/A"}\n`;
      });
      content += `\n`;
    }
    if (state.similar_projects?.length) {
      content += `## Similar Projects (${state.similar_projects.length} repos)\n`;
      state.similar_projects.forEach((proj, i) => {
        content += `${i + 1}. **${proj.name}** (${proj.similarity_score}% match)\n`;
      });
      content += `\n`;
    }
    if (state.gaps) content += `## Research Gaps\n\`\`\`json\n${JSON.stringify(state.gaps, null, 2)}\n\`\`\`\n\n`;
    if (state.technical_plan) content += `## Technical Plan\n\`\`\`json\n${JSON.stringify(state.technical_plan, null, 2)}\n\`\`\`\n\n`;
    if (state.teaching_plan) content += `## Teaching Plan\n\`\`\`json\n${JSON.stringify(state.teaching_plan, null, 2)}\n\`\`\`\n\n`;

    if (messages?.length) {
      content += `## Chat Transcript\n`;
      messages.forEach((m) => {
        content += `**${m.role.toUpperCase()}**: ${m.content}\n\n`;
      });
    }

    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `consiliai-export-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    const exportData = {
      exported_at: new Date().toISOString(),
      state: state || {},
      messages: messages || []
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `consiliai-export-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadProject = async () => {
    const targetId = selectedExportProject || activeConversationId || conversations?.[0]?.id;
    if (!targetId) {
      toast({
        title: "No project selected",
        description: "Please select or create a conversation first.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsDownloadingProject(true);
    try {
      await downloadProjectZip(targetId);
      toast({
        title: "Project downloaded",
        description: "Your organized project archive (.zip) has been downloaded.",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
    } catch (err) {
      toast({
        title: "Download failed",
        description: err.message,
        status: "error",
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setIsDownloadingProject(false);
    }
  };

  const handleConfirmDeleteAllData = async () => {
    if (deleteAllConfirmText !== "DELETE") return;
    setIsDeletingAll(true);
    try {
      await deleteAllUserData();
      toast({
        title: "All user data deleted",
        description: "All conversations, plans, courses, labs, and uploaded files have been permanently removed.",
        status: "info",
        duration: 4000,
        isClosable: true,
      });
      setIsDeleteAllModalOpen(false);
      onClose(); // close settings modal
      if (onDeleteAllData) {
        onDeleteAllData();
      }
    } catch (err) {
      toast({
        title: "Deletion failed",
        description: err.message,
        status: "error",
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setIsDeletingAll(false);
    }
  };

  const startResizing = (e) => {
    e.preventDefault();
    setIsResizing(true);

    const onMouseMove = (moveEvent) => {
      const newWidth = moveEvent.clientX;
      if (newWidth >= 200 && newWidth <= 400) {
        setSidebarWidth(newWidth);
      }
    };

    const onMouseUp = () => {
      setIsResizing(false);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  };

  return (
    <Box
      w={isCollapsed ? "0px" : `${sidebarWidth}px`}
      flexShrink={0}
      bg={bgSidebar}
      borderRight={isCollapsed ? "none" : "1px solid"}
      borderColor={borderColor}
      p={isCollapsed ? 0 : 5}
      opacity={isCollapsed ? 0 : 1}
      overflow="hidden"
      display="flex"
      flexDirection="column"
      position="relative"
      userSelect={isResizing ? "none" : "auto"}
      transition={isResizing ? "none" : "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)"}
    >
      {/* Resizable Drag Handle */}
      {!isCollapsed && (
        <Box
          position="absolute"
          right="0"
          top="0"
          bottom="0"
          w="5px"
          cursor="col-resize"
          _hover={{ bg: "gold.400" }}
          bg={isResizing ? "gold.500" : "transparent"}
          onMouseDown={startResizing}
          zIndex={10}
        />
      )}

      <HStack justify="space-between" mb={6} align="center">
        <HStack spacing={2} align="center">
          {onToggleCollapse && (
            <Tooltip label="Collapse left sidebar" placement="bottom-start">
              <IconButton
                icon={<FiChevronLeft />}
                size="xs"
                variant="ghost"
                color={textSubtle}
                _hover={{ bg: bgHover, color: textPrimary }}
                aria-label="Collapse left sidebar"
                onClick={onToggleCollapse}
              />
            </Tooltip>
          )}
          <Image 
            src="/logo.png" 
            alt="ConsiliAI Logo" 
            h="75px"
            maxW="100px"
            objectFit="contain" 
            fallback={
              <Text fontFamily="mono" fontSize="xs" color={textSubtle} letterSpacing="wide">
                [ CONSILIAI ]
              </Text>
            }
          />
        </HStack>
        <Button size="xs" variant="outline" onClick={onNewChat}>
          + New Chat
        </Button>
      </HStack>
      
      <VStack align="stretch" spacing={1} flex="1" overflowY="auto" mb={4}>
        {(conversations || []).map((c) => (
          <HStack 
            key={c.id} 
            bg={activeConversationId === c.id ? bgCard : "transparent"}
            _hover={{ bg: bgHover }}
            boxShadow="-4px 0px 24px rgba(30,25,17,0.06)"
            p={2}
            borderRadius="md"
            cursor="pointer"
            onClick={() => onSelectConversation(c.id)}
          >
            <Text 
              fontSize="sm" 
              flex="1" 
              noOfLines={1} 
              color={activeConversationId === c.id ? textPrimary : textSecondary} 
              fontWeight={activeConversationId === c.id ? "bold" : "normal"}
            >
              {c.title}
            </Text>
            <IconButton 
              icon={<FiX />} 
              size="xs" 
              variant="ghost" 
              color="red.400"
              aria-label="Delete chat"
              onClick={(e) => { e.stopPropagation(); setChatToDelete(c); }}
            />
          </HStack>
        ))}
      </VStack>

      <Box pt={4} borderTop="1px solid" borderColor={borderColor}> 
        <Button 
          width="100%" 
          variant="ghost" 
          leftIcon={<FiSettings />} 
          onClick={onOpen}
          color={textPrimary}
          bg="gold.900"
          _hover={{ bg: bgHover }}
        >
          Settings
        </Button>
      </Box>

      {/* Settings Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="lg">
        <ModalOverlay />
        <ModalContent bg={bgSidebar} borderRadius="card" boxShadow="card">
          <ModalHeader color={textPrimary} borderBottom="1px solid" borderColor={borderColor}>
            Settings
          </ModalHeader>
          <ModalCloseButton color={textSubtle} />
          <ModalBody py={4}>
            <Tabs variant="soft-rounded" colorScheme="orange" size="sm">
              <TabList mb={4} gap={1} overflowX="auto">
                <Tab><FiUser style={{ marginRight: 6 }} /> Account & Session</Tab>
                <Tab><FiDownload style={{ marginRight: 6 }} /> Export & Data</Tab>
                <Tab><FiSliders style={{ marginRight: 6 }} /> Appearance</Tab>
                <Tab><FiCpu style={{ marginRight: 6 }} /> Model & Provider</Tab>
              </TabList>

              <TabPanels>
                {/* Account & Session */}
                <TabPanel p={0}>
                  <VStack align="stretch" spacing={4}>
                    <Box p={4} {...SECTION_CARD} borderColor={borderColor}>
                      <Text fontSize="xs" fontWeight="bold" color={textSubtle} mb={1} letterSpacing="wider">
                        USER PROFILE
                      </Text>
                      <Text fontSize="sm" fontWeight="bold" color={textPrimary}>
                        {userData?.email || "Authenticated User"}
                      </Text>
                      <HStack spacing={2} mt={2}>
                        <Badge colorScheme="green" borderRadius="full" px={2}>Active Session</Badge>
                        {userData?.is_superuser && <Badge colorScheme="purple" borderRadius="full" px={2}>Admin</Badge>}
                      </HStack>
                    </Box>

                    {onLogout && (
                      <Box pt={2}>
                        <Button 
                          variant="outline" 
                          colorScheme="red" 
                          width="100%" 
                          onClick={() => {
                            onClose();
                            onLogout();
                          }}
                        >
                          Sign out
                        </Button>
                      </Box>
                    )}
                  </VStack>
                </TabPanel>

                {/* Export & Data Management */}
                <TabPanel p={0}>
                  <VStack align="stretch" spacing={4}>
                    {/* Export Ledger */}
                    <Box p={4} {...SECTION_CARD} borderColor={borderColor}>
                      <Text fontSize="xs" fontWeight="bold" color={textSubtle} mb={2} letterSpacing="wider">
                        EXPORT RESEARCH LEDGER
                      </Text>
                      <Text fontSize="xs" color={textSecondary} mb={3}>
                        Download your active project ideas, literature analysis, gaps, and chat transcript.
                      </Text>
                      <HStack spacing={3}>
                        <Button 
                          size="sm" 
                          variant="solid" 
                          bg="gold.500" 
                          color="white" 
                          leftIcon={<FiFileText />} 
                          onClick={handleExportMarkdown}
                        >
                          Export Markdown (.md)
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          leftIcon={<FiCode />} 
                          onClick={handleExportJSON}
                        >
                          Export JSON
                        </Button>
                      </HStack>
                    </Box>

                    {/* Global Project Download */}
                    <Box p={4} {...SECTION_CARD} borderColor={borderColor}>
                      <Text fontSize="xs" fontWeight="bold" color={textSubtle} mb={2} letterSpacing="wider">
                        DOWNLOAD FULL PROJECT ARCHIVE (ZIP)
                      </Text>
                      <Text fontSize="xs" color={textSecondary} mb={3}>
                        Download all content generated for a project in a single organized ZIP archive (courses, labs, exercises, plans, experiments, notebooks, documents, code, and transcripts).
                      </Text>
                      <VStack align="stretch" spacing={3}>
                        {(conversations || []).length > 1 && (
                          <Box>
                            <Text fontSize="xs" color={textSubtle} mb={1}>Select Project / Conversation:</Text>
                            <Select 
                              size="sm" 
                              borderRadius="md" 
                              value={selectedExportProject || activeConversationId || (conversations[0]?.id)}
                              onChange={(e) => setSelectedExportProject(e.target.value)}
                            >
                              {conversations.map((c) => (
                                <option key={c.id} value={c.id}>
                                  {c.title}
                                </option>
                              ))}
                            </Select>
                          </Box>
                        )}
                        <Button 
                          size="sm" 
                          variant="solid" 
                          bg="gold.500" 
                          color="white" 
                          _hover={{ bg: "gold.600" }}
                          leftIcon={<FiDownload />} 
                          isLoading={isDownloadingProject}
                          loadingText="Preparing ZIP..."
                          onClick={handleDownloadProject}
                        >
                          Download Project (ZIP)
                        </Button>
                      </VStack>
                    </Box>

                    {/* Delete All User Data (Replaces Delete Current Chat) */}
                    <Box p={4} bg={useColorModeValue("red.50", "rgba(220, 38, 38, 0.1)")} borderRadius="control" border="1px solid" borderColor={useColorModeValue("red.200", "red.700")}>
                      <HStack spacing={2} mb={2} color="red.500">
                        <FiAlertTriangle />
                        <Text fontSize="xs" fontWeight="bold" letterSpacing="wider">
                           DELETE ALL USER DATA
                        </Text>
                      </HStack>
                      <Text fontSize="xs" color={textSecondary} mb={3}>
                        Permanently remove all data belonging to your account across the platform: all chats, plans, courses, lab exercises, notebooks, experiments, and uploaded documents.
                      </Text>
                      <Button 
                        size="sm" 
                        colorScheme="red" 
                        leftIcon={<FiTrash2 />}
                        onClick={() => {
                          setDeleteAllConfirmText("");
                          setIsDeleteAllModalOpen(true);
                        }}
                      >
                        Delete All User Data
                      </Button>
                    </Box>
                  </VStack>
                </TabPanel>

                {/* Appearance & Interface */}
                <TabPanel p={0}>
                  <VStack align="stretch" spacing={4}>
                    <Box p={4} {...SECTION_CARD} borderColor={borderColor}>
                      <Text fontSize="xs" fontWeight="bold" color={textSubtle} mb={2} letterSpacing="wider">
                        COLOR MODE
                      </Text>
                      <RadioGroup value={colorMode} onChange={(val) => setColorMode(val)}>
                        <Stack direction="row" spacing={6}>
                          <Radio value="light" colorScheme="orange">
                            <HStack spacing={1}>
                              <FiSun />
                              <Text>Light Mode</Text>
                            </HStack>
                          </Radio>
                          <Radio value="dark" colorScheme="orange">
                            <HStack spacing={1}>
                              <FiMoon />
                              <Text>Dark Mode</Text>
                            </HStack>
                          </Radio>
                        </Stack>
                      </RadioGroup>
                    </Box>

                    <Box p={4} {...SECTION_CARD} borderColor={borderColor}>
                      <Text fontSize="xs" fontWeight="bold" color={textSubtle} mb={2} letterSpacing="wider">
                        CHAT LAYOUT DENSITY
                      </Text>
                      <RadioGroup value={density} onChange={handleDensityChange}>
                        <Stack direction="row" spacing={4}>
                          <Radio value="comfortable" colorScheme="orange">Comfortable</Radio>
                          <Radio value="compact" colorScheme="orange">Compact</Radio>
                        </Stack>
                      </RadioGroup>
                    </Box>
                  </VStack>
                </TabPanel>

                {/* Model & Provider Selection */}
                <TabPanel p={0}>
                  <VStack align="stretch" spacing={4}>
                    <Box p={4} {...SECTION_CARD} borderColor={borderColor}>
                      <Text fontSize="xs" fontWeight="bold" color={textSubtle} mb={2} letterSpacing="wider">
                        LLM INFERENCE PROVIDER
                      </Text>
                      <Text fontSize="xs" color={textSecondary} mb={4}>
                        Select which model backend powers generation, tool execution, and code synthesis across ConsiliAI.
                      </Text>
                      <RadioGroup value={llmProvider} onChange={handleProviderChange} isDisabled={isUpdatingProvider}>
                        <VStack align="stretch" spacing={3}>
                          <Box
                            p={3}
                            borderRadius="control"
                            border="1px solid"
                            borderColor={llmProvider === "cloud" ? "gold.500" : borderColor}
                            bg={llmProvider === "cloud" ? useColorModeValue("orange.50", "whiteAlpha.100") : "transparent"}
                          >
                            <Radio value="cloud" colorScheme="orange">
                              <HStack spacing={2} align="center">
                                <Text fontWeight="semibold" fontSize="sm" color={textPrimary}>Cloud (Groq + Gemini)</Text>
                                <Badge colorScheme="green" borderRadius="full" px={2} fontSize="10px">Default</Badge>
                              </HStack>
                            </Radio>
                            <Text fontSize="xs" color={textSubtle} ml={6} mt={1}>
                              Primary reasoning via Groq (Qwen 2.5 27B), lightweight tasks via Gemini 1.5 Flash. Fast, robust, recommended.
                            </Text>
                          </Box>

                          <Box
                            p={3}
                            borderRadius="control"
                            border="1px solid"
                            borderColor={llmProvider === "local" ? "gold.500" : borderColor}
                            bg={llmProvider === "local" ? useColorModeValue("orange.50", "whiteAlpha.100") : "transparent"}
                          >
                            <Radio value="local" colorScheme="orange">
                              <HStack spacing={2} align="center">
                                <Text fontWeight="semibold" fontSize="sm" color={textPrimary}>Local (Ollama)</Text>
                                {llmProvider === "local" && <Badge colorScheme="orange" borderRadius="full" px={2} fontSize="10px">Active</Badge>}
                              </HStack>
                            </Radio>
                            <Text fontSize="xs" color={textSubtle} ml={6} mt={1}>
                              Routes generation to your local Ollama server (llama3.1:8b for reasoning, qwen2.5-coder:7b for Lab Agent). Gracefully falls back to Cloud if Ollama is unreachable.
                            </Text>
                          </Box>
                        </VStack>
                      </RadioGroup>
                    </Box>
                  </VStack>
                </TabPanel>
              </TabPanels>

            </Tabs>
          </ModalBody>
          <ModalFooter borderTop="1px solid" borderColor={borderColor}>
           {/*  <Button variant="ghost" size="sm" onClick={onClose}>
              Close
            </Button> */}
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Sidebar Chat Deletion Confirmation Modal */}
      <Modal isOpen={Boolean(chatToDelete)} onClose={() => setChatToDelete(null)} isCentered size="md">
        <ModalOverlay />
        <ModalContent bg={bgSidebar} borderRadius="card" boxShadow="card">
          <ModalHeader color={textPrimary} borderBottom="1px solid" borderColor={borderColor}>
            <HStack spacing={2}>
              <FiTrash2 color="red" />
              <Text>Delete Conversation</Text>
            </HStack>
          </ModalHeader>
          <ModalCloseButton color={textSubtle} />
          <ModalBody py={4}>
            <VStack align="stretch" spacing={3}>
              <Text fontSize="sm" color={textPrimary}>
                Are you sure you want to delete this conversation?
              </Text>
              <Box p={3} bg={bgCard} borderRadius="md" border="1px solid" borderColor={borderColor}>
                <Text fontWeight="bold" fontSize="sm" color={textPrimary} noOfLines={2}>
                  {chatToDelete?.title}
                </Text>
              </Box>
              <Text fontSize="xs" color={useColorModeValue("red.600", "red.400")}>
                This conversation and its message history will be permanently deleted. This action cannot be undone.
              </Text>
            </VStack>
          </ModalBody>
          <ModalFooter borderTop="1px solid" borderColor={borderColor} gap={2}>
            <Button variant="ghost" size="sm" onClick={() => setChatToDelete(null)}>
              Cancel
            </Button>
            <Button
              colorScheme="red"
              size="sm"
              leftIcon={<FiTrash2 />}
              onClick={() => {
                if (chatToDelete?.id) {
                  const id = chatToDelete.id;
                  setChatToDelete(null);
                  onDeleteChat(id);
                }
              }}
            >
              Delete
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Delete All User Data Confirmation Modal */}
      <Modal
        isOpen={isDeleteAllModalOpen}
        onClose={() => !isDeletingAll && setIsDeleteAllModalOpen(false)}
        isCentered
        size="lg"
      >
        <ModalOverlay />
        <ModalContent bg={bgSidebar} borderRadius="card" boxShadow="card">
          <ModalHeader color="red.500" borderBottom="1px solid" borderColor={borderColor}>
            <HStack spacing={2}>
              <FiAlertTriangle />
              <Text>Delete All User Data</Text>
            </HStack>
          </ModalHeader>
          <ModalCloseButton isDisabled={isDeletingAll} color={textSubtle} />
          <ModalBody py={4}>
            <VStack align="stretch" spacing={4}>
              <Box
                p={4}
                bg={useColorModeValue("red.50", "rgba(220, 38, 38, 0.15)")}
                borderRadius="md"
                border="1px solid"
                borderColor={useColorModeValue("red.300", "red.800")}
              >
                <Text fontSize="sm" fontWeight="bold" color="red.600" _dark={{ color: "red.200" }} mb={2}>
                  Permanent & Destructive Action
                </Text>
                <Text fontSize="xs" color={useColorModeValue("red.800", "red.200")} mb={2}>
                  This action will permanently delete <strong>all data</strong> belonging to your account, not just the current conversation. This includes:
                </Text>
                <VStack align="stretch" spacing={1} pl={2} fontSize="xs" color={useColorModeValue("red.800", "red.300")}>
                  <Text>• All chats and conversation histories</Text>
                  <Text>• All generated courses, lesson materials, and presentations</Text>
                  <Text>• All lab exercises, starter code, solutions, and Jupyter notebooks</Text>
                  <Text>• All technical plans, teaching plans, and novelty analyses</Text>
                  <Text>• All identified research gaps and experiment designs</Text>
                  <Text>• All uploaded documents, PDFs, and vector embeddings</Text>
                </VStack>
              </Box>

              <Box>
                <Text fontSize="xs" fontWeight="semibold" mb={2} color={textPrimary}>
                  To confirm permanent deletion, type <Text as="span" fontWeight="bold" color="red.500">DELETE</Text> below:
                </Text>
                <Input
                  placeholder="Type DELETE to confirm"
                  value={deleteAllConfirmText}
                  onChange={(e) => setDeleteAllConfirmText(e.target.value)}
                  focusBorderColor="red.500"
                  size="sm"
                  borderRadius="md"
                  isDisabled={isDeletingAll}
                />
              </Box>
            </VStack>
          </ModalBody>
          <ModalFooter borderTop="1px solid" borderColor={borderColor} gap={2}>
            <Button variant="ghost" size="sm" onClick={() => setIsDeleteAllModalOpen(false)} isDisabled={isDeletingAll}>
              Cancel
            </Button>
            <Button
              colorScheme="red"
              size="sm"
              leftIcon={<FiTrash2 />}
              isDisabled={deleteAllConfirmText !== "DELETE" || isDeletingAll}
              isLoading={isDeletingAll}
              loadingText="Deleting Everything..."
              onClick={handleConfirmDeleteAllData}
            >
              Permanently Delete All Data
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}