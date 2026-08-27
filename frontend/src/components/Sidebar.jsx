import { useState } from "react";
import {
  Box,
  Text,
  VStack,
  HStack,
  Badge,
  Divider,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Link,
  Code,
} from "@chakra-ui/react";

function LedgerRow({ index, label, detail, done, onClick }) {
  return (
    <HStack
      align="start"
      spacing={3}
      py={3}
      px={2}
      borderRadius="md"
      cursor={done ? "pointer" : "default"}
      _hover={done ? { bg: "paper.200" } : {}}
      onClick={done ? onClick : undefined}
      transition="background 0.2s"
    >
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
          view
        </Badge>
      )}
    </HStack>
  );
}

export default function Sidebar({ state }) {
  const [selectedSection, setSelectedSection] = useState(null);
  const [drawerSize, setDrawerSize] = useState("md"); // md, lg, xl, full
  const [sidebarWidth, setSidebarWidth] = useState(300);
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = (e) => {
    e.preventDefault();
    setIsResizing(true);

    const onMouseMove = (moveEvent) => {
      const newWidth = window.innerWidth - moveEvent.clientX;
      if (newWidth >= 220 && newWidth <= 600) {
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

  const s = state || {};
  const papers = s.papers || [];
  const papersCount = papers.length;
  const similarProjects = s.similar_projects || [];
  const projectsCount = similarProjects.length;
  const gaps = s.gaps || [];
  const gapsCount = gaps.length;
  const experiments = s.experiments?.experiments || [];
  const experimentsCount = experiments.length;

  const rows = [
    {
      id: "idea",
      label: "Idea",
      detail: s.idea || "Not set yet",
      done: Boolean(s.idea),
    },
    {
      id: "literature",
      label: "Literature",
      detail: papersCount ? `${papersCount} paper(s) analyzed` : "Not fetched yet",
      done: papersCount > 0,
    },
    {
      id: "similar_projects",
      label: "Similar Projects",
      detail: projectsCount ? `${projectsCount} repo(s) found` : "Not searched yet",
      done: projectsCount > 0,
    },
    {
      id: "gaps",
      label: "Research gaps",
      detail: gapsCount ? `${gapsCount} gap(s) found` : "Not run yet",
      done: gapsCount > 0,
    },
    {
      id: "technical_plan",
      label: "Technical plan",
      detail: s.technical_plan ? "Generated" : "Not generated",
      done: Boolean(s.technical_plan),
    },
    {
      id: "teaching_plan",
      label: "Teaching plan",
      detail: s.teaching_plan ? "Generated" : "Not generated",
      done: Boolean(s.teaching_plan),
    },
    {
      id: "course",
      label: "Course",
      detail: s.course ? "Generated" : "Not generated",
      done: Boolean(s.course),
    },
    {
      id: "experiments",
      label: "Experiments",
      detail: experimentsCount ? `${experimentsCount} experiment(s)` : "Not generated",
      done: experimentsCount > 0,
    },
  ];

  return (
    <Box
      w={`${sidebarWidth}px`}
      flexShrink={0}
      bg="paper.50"
      borderLeft="1px solid"
      borderColor="paper.300"
      p={5}
      overflowY="auto"
      position="relative"
      userSelect={isResizing ? "none" : "auto"}
    >
      {/* Resizable Drag Handle */}
      <Box
        position="absolute"
        left="0"
        top="0"
        bottom="0"
        w="5px"
        cursor="col-resize"
        _hover={{ bg: "gold.400" }}
        bg={isResizing ? "gold.500" : "transparent"}
        onMouseDown={startResizing}
        zIndex={10}
      />

      <Text fontFamily="mono" fontSize="xs" color="slate.500" letterSpacing="wide" mb={4}>
        [ RESEARCH LEDGER ]
      </Text>
      <VStack align="stretch" spacing={0} divider={<Divider borderColor="paper.200" />}>
        {rows.map((row, i) => (
          <LedgerRow
            key={row.id}
            index={i + 1}
            {...row}
            onClick={() => setSelectedSection(row.id)}
          />
        ))}
      </VStack>

      {/* Transparency Drawer */}
      <Drawer
        isOpen={Boolean(selectedSection)}
        placement="right"
        size={drawerSize}
        onClose={() => setSelectedSection(null)}
      >
        <DrawerOverlay />
        <DrawerContent bg="paper.50">
          <DrawerCloseButton />
          <DrawerHeader borderBottomWidth="1px" borderColor="paper.300" fontFamily="mono" fontSize="md">
            <HStack justify="space-between" pr={8}>
              <Text>[{selectedSection?.toUpperCase()}]</Text>
              <HStack spacing={1}>
                <Badge cursor="pointer" colorScheme={drawerSize === "md" ? "gold" : "gray"} onClick={() => setDrawerSize("md")}>
                  Normal
                </Badge>
                <Badge cursor="pointer" colorScheme={drawerSize === "lg" ? "gold" : "gray"} onClick={() => setDrawerSize("lg")}>
                  Large
                </Badge>
                <Badge cursor="pointer" colorScheme={drawerSize === "full" ? "gold" : "gray"} onClick={() => setDrawerSize("full")}>
                  Full Screen
                </Badge>
              </HStack>
            </HStack>
          </DrawerHeader>
          <DrawerBody py={6}>
            {selectedSection === "literature" && (
              <VStack align="stretch" spacing={5}>
                <Text fontSize="md" color="ink.800" fontWeight="600" mb={1}>
                  Full breakdown of analyzed literature papers with clickable source URLs, sections detected, and extracted methodologies:
                </Text>
                {papers.map((paper, idx) => {
                  // DEBUG: log each paper object to browser console
                  console.log(`[Sidebar paper ${idx}]`, JSON.stringify({ title: paper.title, url: paper.url, pdf_url: paper.pdf_url, source: paper.source }));
                  const rawSrc = String(paper.source || "").toLowerCase();
                  let paperSource = "ACADEMIC PUBLICATION";
                  if (rawSrc.includes("arxiv") || paper.url?.includes("arxiv")) {
                    paperSource = "ARXIV";
                  } else if (rawSrc.includes("semantic") || paper.url?.includes("semanticscholar")) {
                    paperSource = "SEMANTIC SCHOLAR";
                  } else if (rawSrc.includes("openalex") || paper.url?.includes("openalex")) {
                    paperSource = "OPENALEX";
                  } else if (rawSrc.includes("upload") || rawSrc.includes("user")) {
                    paperSource = "USER UPLOADED DOCUMENT";
                  } else if (paper.source && paper.source !== "N/A") {
                    paperSource = String(paper.source).toUpperCase().replace("_", " ");
                  }
                  
                  return (
                    <Box
                      key={idx}
                      p={5}
                      bg="white"
                      borderRadius="lg"
                      border="1.5px solid"
                      borderColor="paper.300"
                      boxShadow="md"
                    >
                      <HStack justify="space-between" mb={3} align="center">
                        <Badge colorScheme="purple" px={3} py={1} borderRadius="md" fontSize="xs" fontWeight="bold">
                          {paperSource}
                        </Badge>
                        <HStack spacing={3}>
                          {paper.url && (
                            <Link 
                              href={paper.url} 
                              target="_blank" 
                              rel="noopener noreferrer" 
                              fontSize="sm" 
                              color="blue.600" 
                              fontWeight="bold"
                              _hover={{ textDecoration: "underline", color: "blue.800" }}
                            >
                              🔗 [Open Article Link]
                            </Link>
                          )}
                          {paper.pdf_url && (
                            <Link 
                              href={paper.pdf_url} 
                              target="_blank" 
                              rel="noopener noreferrer" 
                              fontSize="sm" 
                              color="teal.600" 
                              fontWeight="bold"
                              _hover={{ textDecoration: "underline", color: "teal.800" }}
                            >
                              📄 [Download PDF]
                            </Link>
                          )}
                        </HStack>
                      </HStack>

                      <Text fontWeight="bold" fontSize="md" color="ink.900" mb={2} lineHeight="short">
                        {paper.title}
                      </Text>

                      {paper.authors?.length > 0 && (
                        <Text fontSize="sm" color="ink.700" mb={3}>
                          <b>Authors:</b> {Array.isArray(paper.authors) ? paper.authors.join(", ") : paper.authors}
                        </Text>
                      )}
                      
                      {paper.url ? (
                        <Box bg="paper.100" p={2.5} borderRadius="md" mb={3} border="1px solid" borderColor="paper.300">
                          <Text fontSize="xs" color="slate.600" fontWeight="bold" mb={1}>DIRECT PUBLICATION URL:</Text>
                          <Link 
                            href={paper.url} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            fontSize="sm" 
                            color="blue.600" 
                            fontWeight="bold"
                            wordBreak="break-all"
                            _hover={{ textDecoration: "underline", color: "blue.800" }}
                          >
                            {paper.url}
                          </Link>
                        </Box>
                      ) : (
                        <Box bg="orange.50" p={2} borderRadius="md" mb={3} border="1px solid" borderColor="orange.200">
                          <Text fontSize="xs" color="orange.800">
                            📄 User-uploaded local document (No public web URL).
                          </Text>
                        </Box>
                      )}

                      {paper.sections_detected?.length > 0 && (
                        <HStack spacing={1.5} mb={3} wrap="wrap">
                          <Text fontSize="xs" color="ink.600" fontWeight="bold">Extracted Sections:</Text>
                          {paper.sections_detected.map((sec) => (
                            <Badge key={sec} fontSize="xs" px={2} py={0.5} colorScheme="teal" borderRadius="sm">
                              {sec}
                            </Badge>
                          ))}
                        </HStack>
                      )}

                      {paper.analysis && Object.keys(paper.analysis).length > 0 && (
                        <Accordion allowToggle size="md" mt={3}>
                          <AccordionItem border="none">
                            <AccordionButton px={3} py={2} bg="paper.100" borderRadius="md" _hover={{ bg: "paper.200" }}>
                              <Box flex="1" textAlign="left" fontSize="sm" fontWeight="bold" color="slate.700">
                                View Section Methodologies & Results
                              </Box>
                              <AccordionIcon />
                            </AccordionButton>
                            <AccordionPanel pb={3} px={1} pt={3} maxH="400px" overflowY="auto">
                              <VStack align="stretch" spacing={3} fontSize="sm">
                                {Object.entries(paper.analysis).map(([secKey, secVal]) => (
                                  <Box key={secKey} bg="paper.50" p={3} border="1px solid" borderColor="paper.300" borderRadius="md">
                                    <Text fontWeight="bold" fontSize="sm" color="teal.800" mb={1.5}>
                                      {secKey.toUpperCase()}
                                    </Text>
                                    {typeof secVal === "object" ? (
                                      Object.entries(secVal).map(([k, v]) => (
                                        <Text key={k} color="ink.800" fontSize="sm" mb={1}>
                                          <b>{k.replace("_", " ")}:</b> {typeof v === "object" ? JSON.stringify(v) : String(v)}
                                        </Text>
                                      ))
                                    ) : (
                                      <Text color="ink.800" fontSize="sm">{String(secVal)}</Text>
                                    )}
                                  </Box>
                                ))}
                              </VStack>
                            </AccordionPanel>
                          </AccordionItem>
                        </Accordion>
                      )}
                    </Box>
                  );
                })}
              </VStack>
            )}

            {selectedSection === "similar_projects" && (
              <VStack align="stretch" spacing={4}>
                <Text fontSize="sm" color="ink.600" mb={2}>
                  Similar repositories & projects discovered across GitHub, Hugging Face, Kaggle, and GitLab:
                </Text>
                {similarProjects.map((proj, idx) => (
                  <Box
                    key={idx}
                    p={4}
                    bg="white"
                    borderRadius="md"
                    border="1px solid"
                    borderColor="paper.300"
                    boxShadow="sm"
                  >
                    <HStack justify="space-between" mb={2}>
                      <Badge colorScheme="blue">{proj.source || "Code"}</Badge>
                      <Badge colorScheme="green">{proj.similarity_score}% Match</Badge>
                    </HStack>
                    <Text fontWeight="bold" fontSize="sm" color="ink.900" mb={1}>
                      {proj.name}
                    </Text>
                    {proj.url && (
                      <Link href={proj.url} isExternal fontSize="xs" color="blue.500" display="block" mb={2}>
                        🔗 {proj.url}
                      </Link>
                    )}
                    {proj.description && (
                      <Text fontSize="xs" color="ink.600">
                        {proj.description}
                      </Text>
                    )}
                  </Box>
                ))}
              </VStack>
            )}

            {selectedSection === "gaps" && (
              <VStack align="stretch" spacing={3}>
                <Text fontSize="sm" color="ink.600">Synthesized Research Gaps:</Text>
                {gaps.map((gap, idx) => (
                  <Box key={idx} p={3} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                    <Text fontWeight="bold" fontSize="xs" color="gold.800" mb={1}>
                      Gap #{idx + 1}: {gap.gap_description}
                    </Text>
                    {gap.supporting_evidence && (
                      <Text fontSize="xs" color="ink.600" mb={2}>
                        <b>Evidence:</b> {gap.supporting_evidence}
                      </Text>
                    )}
                    {gap.papers_involved?.length > 0 && (
                      <Text fontSize="xs" color="slate.500">
                        <b>Papers Involved:</b> {gap.papers_involved.join(", ")}
                      </Text>
                    )}
                  </Box>
                ))}
              </VStack>
            )}

            {selectedSection === "idea" && (
              <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                <Text fontSize="xs" color="slate.500" mb={1}>CURRENT PROJECT IDEA</Text>
                <Text fontSize="sm" fontWeight="bold">{s.idea || "Not set yet"}</Text>
              </Box>
            )}

            {selectedSection === "technical_plan" && (
              <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                <Text fontSize="xs" color="slate.500" mb={2}>TECHNICAL PLAN OVERVIEW</Text>
                <Code display="block" whitespace="pre-wrap" p={3} borderRadius="sm" fontSize="xs">
                  {JSON.stringify(s.technical_plan, null, 2)}
                </Code>
              </Box>
            )}

            {selectedSection === "teaching_plan" && (
              <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                <Text fontSize="xs" color="slate.500" mb={2}>TEACHING PLAN OVERVIEW</Text>
                <Code display="block" whitespace="pre-wrap" p={3} borderRadius="sm" fontSize="xs">
                  {JSON.stringify(s.teaching_plan, null, 2)}
                </Code>
              </Box>
            )}

            {selectedSection === "course" && (
              <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                <Text fontSize="xs" color="slate.500" mb={2}>GENERATED COURSE STRUCTURE</Text>
                <Code display="block" whitespace="pre-wrap" p={3} borderRadius="sm" fontSize="xs">
                  {JSON.stringify(s.course, null, 2)}
                </Code>
              </Box>
            )}

            {selectedSection === "experiments" && (
              <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                <Text fontSize="xs" color="slate.500" mb={2}>GENERATED EXPERIMENTS</Text>
                <Code display="block" whitespace="pre-wrap" p={3} borderRadius="sm" fontSize="xs">
                  {JSON.stringify(s.experiments, null, 2)}
                </Code>
              </Box>
            )}
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </Box>
  );
}
