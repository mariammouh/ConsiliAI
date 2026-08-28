import { Box, Button } from "@chakra-ui/react";
import ReactMarkdown from "react-markdown";

const markdownStyles = {
  "& h1": { fontSize: "lg", fontWeight: "700", mt: 3, mb: 1.5, color: "ink.900" },
  "& h2": { fontSize: "md", fontWeight: "700", mt: 3, mb: 1, color: "ink.900" },
  "& h3": { fontSize: "sm", fontWeight: "700", mt: 2, mb: 1, color: "ink.800" },
  "& p": { mb: 2, lineHeight: "1.7" },
  "& ul": { pl: 5, mb: 2 },
  "& ol": { pl: 5, mb: 2 },
  "& li": { mb: 0.5, lineHeight: "1.6" },
  "& li > p": { mb: 0 },
  "& strong": { fontWeight: "700" },
  "& em": { fontStyle: "italic" },
  "& blockquote": {
    borderLeft: "3px solid",
    borderColor: "gold.400",
    pl: 3,
    ml: 0,
    my: 2,
    color: "ink.600",
    fontStyle: "italic",
  },
  "& code": {
    bg: "paper.200",
    px: 1,
    py: 0.5,
    borderRadius: "sm",
    fontSize: "xs",
    fontFamily: "mono",
  },
  "& pre": {
    bg: "paper.200",
    p: 3,
    borderRadius: "md",
    overflowX: "auto",
    mb: 2,
    fontSize: "xs",
  },
  "& pre code": { bg: "transparent", p: 0 },
  "& a": { color: "blue.600", textDecoration: "underline" },
  "& hr": { my: 3, borderColor: "paper.300" },
  "& table": { width: "100%", mb: 2, fontSize: "xs" },
  "& th": { fontWeight: "700", textAlign: "left", pb: 1, borderBottom: "1px solid", borderColor: "paper.300" },
  "& td": { py: 1, borderBottom: "1px solid", borderColor: "paper.200" },
};

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
      fontSize="sm"
      lineHeight="1.6"
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
