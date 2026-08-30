// frontend/src/theme.js
//
// Visual language borrowed from the Horizon UI Chakra template family:
// soft/diffuse shadows, large corner radii (16–20px), white card surfaces
// on a pale tinted background, pill-shaped active nav states.
//
// Colors are NOT Horizon's (their default is indigo/blue) — this keeps
// your existing paper/ink/gold/slate/sage tokens so the app still looks
// like YOUR system, just with that same polished, cohesive shadow/radius
// treatment layered on top.
//
// Drop-in: same token names your components already use. No component
// files, routes, or logic need to change — only this file.

import { extendTheme } from "@chakra-ui/react";

const colors = {
  paper: {
    50:  "#FFFFFF",
    100: "#efefd0", 
     // your cream — card/panel surfaces FEF9D7 FEFCEB   old :FEFAE0
    200: "#F5EFC9",  // slightly deeper, for chat background vs sidebar contrast
    300: "#E9DFA8", 
    400: "#E2B178", // borders / dividers
    500: "#E5E5B3",
  },
  ink: {
    500: "#8A7F5C",
    600: "#5C5233",
    700: "#3B331C",
    800: "#2A2412",
    900: "#1E1A0C",  // primary text
  },
  gold: {
    50:  "#FBF0DD",
    400: "#DDA15E",  // your tan — lighter accent, hover states
    500: "#BC6C25",  // your ochre — primary accent, buttons, active states
    600: "#9A5A1E",  // pressed/darker
    700: "#934D25",
  },
  slate: {
    500: "#6B6248",
    600: "#544D38",
  },
  sage: {
    500: "#7D8455",
    600: "#636B43",
  },
};
// Horizon's signature diffuse, colored-ish shadow rather than a flat black one
const shadows = {
  card: "0px 18px 40px rgba(42, 36, 28, 0.10)",
  cardHover: "0px 20px 44px rgba(42, 36, 28, 0.14)",
  soft: "0px 4px 12px rgba(42, 36, 28, 0.08)",
};

const radii = {
  card: "20px",
  pill: "9999px",
  control: "12px",
};

const fonts = {
  heading: `'Inter', sans-serif`,
  body: `'Inter', sans-serif`,
  mono: `'IBM Plex Mono', monospace`,
};

const theme = extendTheme({
  colors,
  shadows,
  radii,
  fonts,
  styles: {
    global: {
      body: {
        bg: "paper.200",
        color: "ink.900",
      },
    },
  },
  components: {
    // Generic card wrapper — apply via <Box variant="card"> anywhere you
    // currently have a plain Box/Flex acting as a panel (message groups,
    // ledger panel, sidebar container).
    Card: {
      baseStyle: {
        bg: "paper.100",
        borderRadius: "card",
        boxShadow: "card",
        border: "1px solid",
        borderColor: "paper.300",
      },
    },
    Button: {
      baseStyle: {
        borderRadius: "control",
        fontWeight: "600",
      },
      variants: {
        solid: {
          bg: "gold.500",
          color: "white",
          _hover: { bg: "gold.600", boxShadow: "soft" },
        },
        // Sidebar active-conversation state, Horizon-style pill highlight
        navActive: {
          bg: "gold.50",
          color: "gold.600",
          borderRadius: "pill",
          fontWeight: "600",
          justifyContent: "flex-start",
          _hover: { bg: "gold.50" },
        },
        navInactive: {
          bg: "transparent",
          color: "ink.600",
          borderRadius: "pill",
          justifyContent: "flex-start",
          _hover: { bg: "paper.100" },
        },
      },
    },
    Input: {
      baseStyle: {
        field: {
          borderRadius: "control",
          bg: "paper.100",
        },
      },
      defaultProps: { focusBorderColor: "gold.500" },
    },
  },
});

export default theme;