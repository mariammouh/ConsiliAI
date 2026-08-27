import { extendTheme } from "@chakra-ui/react";

/**
 * Design direction: "citation ledger" — this tool turns research papers
 * into education content, so the visual language borrows from annotated
 * manuscripts and citation indices rather than a generic AI-chat look.
 *
 * Color:
 *  - paper (background): warm off-white, like aged paper, not stark white
 *  - ink (text): deep near-black navy, not pure black
 *  - gold (primary accent): muted "highlighter" gold — marginalia, not the
 *    generic AI-terracotta clay tone
 *  - slate (secondary accent): links, secondary actions
 *  - sage (success/positive): gap found, plan generated, etc.
 */
const colors = {
  paper: {
    50: "#FFFFFF",
    100: "#FAF7F0",
    200: "#F1ECE0",
    300: "#E4DCC8",
  },
  ink: {
    500: "#4A5160",
    700: "#2B3240",
    900: "#1A1F2B",
  },
  gold: {
    100: "#F5E9C9",
    400: "#C99A2E",
    500: "#B3872A",
    600: "#96721F",
  },
  slate: {
    400: "#6E88A3",
    500: "#3E5C76",
    600: "#2F4759",
  },
  sage: {
    100: "#E7EBDF",
    400: "#7A8B69",
    500: "#647253",
  },
};

const fonts = {
  heading: `'Source Serif 4', serif`,
  body: `'Inter', sans-serif`,
  mono: `'IBM Plex Mono', monospace`,
};

const theme = extendTheme({
  colors,
  fonts,
  styles: {
    global: {
      body: {
        bg: "paper.100",
        color: "ink.900",
      },
    },
  },
  components: {
    Button: {
      baseStyle: {
        fontWeight: "600",
        borderRadius: "md",
      },
      variants: {
        solid: {
          bg: "gold.400",
          color: "ink.900",
          _hover: { bg: "gold.500" },
          _active: { bg: "gold.600" },
        },
        ghost: {
          color: "slate.500",
          _hover: { bg: "paper.200" },
        },
      },
    },
    Input: {
      variants: {
        outline: {
          field: {
            borderColor: "paper.300",
            bg: "paper.50",
            _focus: {
              borderColor: "gold.400",
              boxShadow: "0 0 0 1px #C99A2E",
            },
          },
        },
      },
    },
  },
});

export default theme;
