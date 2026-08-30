import { Box, Button, useColorModeValue } from "@chakra-ui/react";
import ReactMarkdown from "react-markdown";

export default function MessageBubble({ role, content, downloads = [], onDownload, density = "comfortable" }) {
  const isUser = role === "user";
  const isCompact = density === "compact";

  const bgUser = useColorModeValue("paper.100", "gray.800");
  const colorUser = useColorModeValue("ink.900", "gray.100");
  const borderColorUser = useColorModeValue("paper.300", "gray.700");
  const boxShadowUser = useColorModeValue("0px 2px 8px rgba(30,25,17,0.06)", "0px 2px 8px rgba(0,0,0,0.25)");

  const bgAssistant = useColorModeValue("paper.50", "gray.800");
  const colorAssistant = useColorModeValue("ink.900", "gray.100");
  const borderColorAssistant = useColorModeValue("paper.300", "gray.700");
  const codeBg = useColorModeValue("paper.200", "gray.700");

  const markdownStyles = {
    "& h1": { fontSize: isCompact ? "md" : "lg", fontWeight: "700", mt: 2, mb: 1, color: colorAssistant },
    "& h2": { fontSize: isCompact ? "sm" : "md", fontWeight: "700", mt: 2, mb: 1, color: colorAssistant },
    "& h3": { fontSize: isCompact ? "xs" : "sm", fontWeight: "700", mt: 1.5, mb: 0.5, color: colorAssistant },
    "& p": { mb: isCompact ? 1 : 2, lineHeight: isCompact ? "1.4" : "1.7" },
    "& ul": { pl: 4, mb: isCompact ? 1 : 2 },
    "& ol": { pl: 4, mb: isCompact ? 1 : 2 },
    "& li": { mb: 0.5, lineHeight: isCompact ? "1.4" : "1.6" },
    "& li > p": { mb: 0 },
    "& strong": { fontWeight: "700" },
    "& em": { fontStyle: "italic" },
    "& blockquote": {
      borderLeft: "3px solid",
      borderColor: "gold.400",
      pl: 3,
      ml: 0,
      my: 1.5,
      fontStyle: "italic",
    },
    "& code": {
      bg: codeBg,
      px: 1,
      py: 0.5,
      borderRadius: "sm",
      fontSize: "xs",
      fontFamily: "mono",
    },
    "& pre": {
      bg: codeBg,
      p: isCompact ? 2 : 3,
      borderRadius: "md",
      overflowX: "auto",
      mb: 1.5,
      fontSize: "xs",
    },
    "& pre code": { bg: "transparent", p: 0 },
    "& a": { color: "blue.400", textDecoration: "underline" },
    "& hr": { my: 2, borderColor: borderColorAssistant },
    "& table": { width: "100%", mb: 2, fontSize: "xs" },
    "& th": { fontWeight: "700", textAlign: "left", pb: 1, borderBottom: "1px solid", borderColor: borderColorAssistant },
    "& td": { py: 1, borderBottom: "1px solid", borderColor: borderColorAssistant },
  };

  return (
    <Box
      alignSelf={isUser ? "flex-end" : "flex-start"}
      bg={isUser ? bgUser : bgAssistant}
      color={isUser ? colorUser : colorAssistant}
      border="1px solid"
      borderColor={isUser ? borderColorUser : borderColorAssistant}
      borderRadius={isCompact ? "md" : "14px"}
      boxShadow={isUser ? boxShadowUser : "none"}
      px={isCompact ? 3 : 4}
      py={isCompact ? 2 : 3}
      maxW={isCompact ? "85%" : "72%"}
      fontSize={isCompact ? "xs" : "sm"}
      lineHeight={isCompact ? "1.4" : "1.6"}
      sx={isUser ? {} : markdownStyles}
    >
      {isUser ? (
        <Box whiteSpace="pre-wrap">{content}</Box>
      ) : (
        <ReactMarkdown>{content}</ReactMarkdown>
      )}
      {downloads.map((download) => (
        <Button
          key={download.filename}
          mt={2}
          mr={2}
          size={isCompact ? "xs" : "sm"}
          variant="solid"
          onClick={() => onDownload(download)}
        >
          {download.label}
        </Button>
      ))}
    </Box>
  );
}


