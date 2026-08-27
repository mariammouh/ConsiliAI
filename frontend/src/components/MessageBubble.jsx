import { Box, Button } from "@chakra-ui/react";

export default function MessageBubble({ role, content, downloads = [], onDownload }) {
  const isUser = role === "user";
  return (
    <Box
      alignSelf={isUser ? "flex-end" : "flex-start"}
      bg={isUser ? "ink.900" : "paper.50"}
      color={isUser ? "paper.100" : "ink.900"}
      border={isUser ? "none" : "1px solid"}
      borderColor="paper.300"
      borderRadius="lg"
      px={4}
      py={3}
      maxW="72%"
      whiteSpace="pre-wrap"
      fontSize="sm"
      lineHeight="1.6"
    >
      {content}
      {downloads.map((download) => (
        <Button
          key={download.filename}
          mt={3}
          mr={2}
          size="sm"
          variant="solid"
          onClick={() => onDownload(download)}
        >
          {download.label}
        </Button>
      ))}
    </Box>
  );
}
