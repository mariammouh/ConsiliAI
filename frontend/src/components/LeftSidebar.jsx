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
  useDisclosure,
  useColorMode,
  useColorModeValue,
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
  FiMoon 
} from "react-icons/fi";
import { getUserMe } from "../api.js";

export default function LeftSidebar({ 
  conversations, 
  activeConversationId, 
  onSelectConversation, 
  onNewChat, 
  onDeleteChat,
  onLogout,
  state = {},
  messages = [],
  isCollapsed = false,
  onToggleCollapse,
  density = "comfortable",
  onDensityChange
}) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { colorMode, setColorMode } = useColorMode();
  const [sidebarWidth, setSidebarWidth] = useState(250);
  const [isResizing, setIsResizing] = useState(false);
  const [userData, setUserData] = useState(null);

  const bgSidebar = useColorModeValue("paper.50", "gray.900");
  const borderColor = useColorModeValue("paper.300", "gray.700");
  const bgCard = useColorModeValue("paper.100", "gray.800");
  const bgHover = useColorModeValue("paper.100", "gray.700");
  const textPrimary = useColorModeValue("ink.900", "gray.100");
  const textSecondary = useColorModeValue("ink.600", "gray.400");
  const textSubtle = useColorModeValue("slate.500", "gray.400");
// Consistent card treatment — reuses the theme's own shadow/radius tokens
// instead of ad hoc "sm"/"md"/"xs" values scattered per-box.
const SECTION_CARD = {
  bg: "white",
  borderRadius: "card",     // theme.radii.card → 20px, same everywhere
  border: "1px solid",
  borderColor: "paper.300",
  boxShadow: "soft",        // theme.shadows.soft — same weight as the ledger rows
};

const SECTION_CARD_SUBTLE = {
  bg: "paper.50",
  borderRadius: "control",  // 12px, for nested/inner boxes so hierarchy still reads
  border: "1px solid",
  borderColor: "paper.300",
};
  useEffect(() => {
    if (isOpen) {
      getUserMe().then((data) => {
        if (data) setUserData(data);
      });
    }
  }, [isOpen]);

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
              onClick={(e) => { e.stopPropagation(); onDeleteChat(c.id); }}
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

                    {activeConversationId && (
                      <Box p={4} bg={useColorModeValue("brandy.50", "brandy.900")} borderRadius="control" border="1px solid" borderColor={useColorModeValue("red.200", "red.700")}>
                       {/*  <Text fontSize="xs" fontWeight="bold" color={useColorModeValue("red.700", "red.200")} mb={1} letterSpacing="wider">
                          DANGER ZONE
                        </Text> */}
                        <Text fontSize="xs" color={useColorModeValue("paper.50", "paper.300")} mb={3}>
                          Permanently remove the active conversation and reset local state.
                        </Text>
                        <Button 
                          size="sm" 
                          bg={useColorModeValue("brandy.900", "brandy.900")}
                          _hover={{ bg: "brandy.50"}}
                          colorScheme="red" 
                          leftIcon={<FiTrash2 />}
                          onClick={() => {
                            onDeleteChat(activeConversationId);
                            onClose();
                          }}
                        >
                          Delete Current Chat
                        </Button>
                      </Box>
                    )}
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
    </Box>
  );
}