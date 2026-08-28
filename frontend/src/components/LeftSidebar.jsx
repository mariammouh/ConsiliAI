import { useState } from "react";
import {
  Box,
  Text,
  VStack,
  HStack,
  Button,
  IconButton,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  useDisclosure,
} from "@chakra-ui/react";

export default function LeftSidebar({ 
  conversations, 
  activeConversationId, 
  onSelectConversation, 
  onNewChat, 
  onDeleteChat 
}) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [sidebarWidth, setSidebarWidth] = useState(250);
  const [isResizing, setIsResizing] = useState(false);

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
      w={`${sidebarWidth}px`}
      flexShrink={0}
      bg="paper.50"
      borderRight="1px solid"
      borderColor="paper.300"
      p={5}
      display="flex"
      flexDirection="column"
      position="relative"
      userSelect={isResizing ? "none" : "auto"}
    >
      {/* Resizable Drag Handle */}
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

      <HStack justify="space-between" mb={6}>
        <Text fontFamily="mono" fontSize="xs" color="slate.500" letterSpacing="wide">
          [ CONVERSATIONS ]
        </Text>
        <Button size="xs" variant="outline" onClick={onNewChat}>
          + New Chat
        </Button>
      </HStack>
      
      <VStack align="stretch" spacing={1} flex="1" overflowY="auto" mb={4}>
        {(conversations || []).map((c) => (
          <HStack 
            key={c.id} 
            bg={activeConversationId === c.id ? "paper.200" : "transparent"}
            _hover={{ bg: "paper.200" }}
            p={2}
            borderRadius="md"
            cursor="pointer"
            onClick={() => onSelectConversation(c.id)}
          >
            <Text fontSize="sm" flex="1" noOfLines={1} color={activeConversationId === c.id ? "ink.900" : "ink.600"} fontWeight={activeConversationId === c.id ? "bold" : "normal"}>
              {c.title}
            </Text>
            <IconButton 
              icon={<Text fontSize="xs">✕</Text>} 
              size="xs" 
              variant="ghost" 
              color="red.400"
              aria-label="Delete chat"
              onClick={(e) => { e.stopPropagation(); onDeleteChat(c.id); }}
            />
          </HStack>
        ))}
      </VStack>

      <Box pt={4} borderTop="1px solid" borderColor="paper.300">
        <Button width="100%" variant="ghost" onClick={onOpen}>
          ⚙ Settings
        </Button>
      </Box>

      {/* Settings Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Settings</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Text fontSize="sm" color="ink.600">
              No settings are currently available in this version. This menu will be expanded in future updates to support agent configurations and user preferences.
            </Text>
          </ModalBody>
          <ModalFooter>
            <Button colorScheme="blue" mr={3} onClick={onClose}>
              Close
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}
