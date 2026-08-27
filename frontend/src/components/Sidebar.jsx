import { Box, Text, VStack, HStack, Badge, Divider } from "@chakra-ui/react";

/**
 * The "citation ledger" signature element: each generated artifact gets a
 * monospace index chip, like a footnote or reference number in a paper.
 * The numbering is real here (order artifacts were generated in this
 * conversation), not decorative.
 */
function LedgerRow({ index, label, detail, done }) {
  return (
    <HStack align="start" spacing={3} py={2}>
      <Text
        fontFamily="mono"
        fontSize="xs"
        color={done ? "gold.600" : "paper.300"}
        minW="28px"
        pt="1px"
      >
        [{String(index).padStart(2, "0")}]
      </Text>
      <Box flex="1">
        <Text fontSize="sm" fontWeight="600" color={done ? "ink.900" : "ink.500"}>
          {label}
        </Text>
        {detail && (
          <Text fontSize="xs" color="ink.500" mt="1px">
            {detail}
          </Text>
        )}
      </Box>
      {done && (
        <Badge bg="sage.100" color="sage.500" fontSize="10px" borderRadius="full" px={2}>
          done
        </Badge>
      )}
    </HStack>
  );
}

export default function Sidebar({ state }) {
  const s = state || {};
  const papersCount = s.papers?.length ?? 0;
  const gapsCount = s.gaps?.length ?? 0;
  const experimentsCount = s.experiments?.experiments?.length ?? 0;

  const rows = [
    {
      label: "Idea",
      detail: s.idea || "Not set yet",
      done: Boolean(s.idea),
    },
    {
      label: "Literature",
      detail: papersCount ? `${papersCount} paper(s) analyzed` : "Not fetched yet",
      done: papersCount > 0,
    },
    {
      label: "Research gaps",
      detail: gapsCount ? `${gapsCount} gap(s) found` : "Not run yet",
      done: gapsCount > 0,
    },
    {
      label: "Technical plan",
      detail: s.technical_plan ? "Generated" : "Not generated",
      done: Boolean(s.technical_plan),
    },
    {
      label: "Teaching plan",
      detail: s.teaching_plan ? "Generated" : "Not generated",
      done: Boolean(s.teaching_plan),
    },
    {
      label: "Course",
      detail: s.course ? "Generated" : "Not generated",
      done: Boolean(s.course),
    },
    {
      label: "Experiments",
      detail: experimentsCount ? `${experimentsCount} experiment(s)` : "Not generated",
      done: experimentsCount > 0,
    },
  ];

  return (
    <Box
      w="300px"
      flexShrink={0}
      bg="paper.50"
      borderLeft="1px solid"
      borderColor="paper.300"
      p={5}
      overflowY="auto"
    >
      <Text fontFamily="mono" fontSize="xs" color="slate.500" letterSpacing="wide" mb={4}>
        [ RESEARCH LEDGER ]
      </Text>
      <VStack align="stretch" spacing={0} divider={<Divider borderColor="paper.200" />}>
        {rows.map((row, i) => (
          <LedgerRow key={row.label} index={i + 1} {...row} />
        ))}
      </VStack>
    </Box>
  );
}
