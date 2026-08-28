import { useState } from "react";
import { downloadArtifact } from "../api.js";
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
  Button,
  IconButton
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
                            <AccordionPanel pb={3} px={1} pt={3} maxH="500px" overflowY="auto">
                              <VStack align="stretch" spacing={4} fontSize="sm">
                                {Object.entries(paper.analysis).map(([secKey, secVal]) => {
                                  // Helper: render a value smartly based on type
                                  const renderValue = (val) => {
                                    if (val == null) return null;
                                    if (Array.isArray(val)) {
                                      if (val.length === 0) return <Text fontSize="xs" color="ink.500" fontStyle="italic">None</Text>;
                                      // Check if it's an array of objects (like reported_numbers)
                                      if (typeof val[0] === "object" && val[0] !== null) {
                                        return null; // handled by special table renderer below
                                      }
                                      return (
                                        <VStack align="stretch" spacing={1} pl={1}>
                                          {val.map((item, i) => (
                                            <HStack key={i} align="start" spacing={2}>
                                              <Text color="slate.400" fontSize="xs" mt="1px" flexShrink={0}>•</Text>
                                              <Text fontSize="xs" color="ink.700" lineHeight="1.6">{String(item)}</Text>
                                            </HStack>
                                          ))}
                                        </VStack>
                                      );
                                    }
                                    return <Text fontSize="xs" color="ink.700" lineHeight="1.6" whiteSpace="pre-wrap">{String(val)}</Text>;
                                  };

                                  // Special renderer for reported_numbers: grouped table
                                  const METRIC_LABELS = {
                                    "A": "Accuracy", "a": "Accuracy", "accuracy": "Accuracy", "Accuracy": "Accuracy",
                                    "P": "Precision", "p": "Precision", "precision": "Precision", "Precision": "Precision",
                                    "R": "Recall", "r": "Recall", "recall": "Recall", "Recall": "Recall",
                                    "F1": "F1-Score", "f1": "F1-Score", "F1-score": "F1-Score", "F1-Score": "F1-Score", "f1-score": "F1-Score",
                                  };
                                  const formatMetric = (m) => METRIC_LABELS[m] || m;

                                  const renderReportedNumbers = (numbers) => {
                                    if (!Array.isArray(numbers) || numbers.length === 0) return null;
                                    // Group by dataset
                                    const byDataset = {};
                                    numbers.forEach((r) => {
                                      const ds = r.dataset || "N/A";
                                      if (!byDataset[ds]) byDataset[ds] = [];
                                      byDataset[ds].push(r);
                                    });
                                    return (
                                      <VStack align="stretch" spacing={3}>
                                        {Object.entries(byDataset).map(([dataset, rows]) => (
                                          <Box key={dataset}>
                                            <Badge colorScheme="blue" fontSize="xs" mb={2}>{dataset}</Badge>
                                            <Box overflowX="auto">
                                              <Box as="table" width="100%" fontSize="xs">
                                                <Box as="thead">
                                                  <Box as="tr" borderBottom="2px solid" borderColor="paper.300">
                                                    <Box as="th" textAlign="left" py={1.5} px={2} color="slate.600" fontWeight="700">Model</Box>
                                                    <Box as="th" textAlign="left" py={1.5} px={2} color="slate.600" fontWeight="700">Metric</Box>
                                                    <Box as="th" textAlign="right" py={1.5} px={2} color="slate.600" fontWeight="700">Value</Box>
                                                  </Box>
                                                </Box>
                                                <Box as="tbody">
                                                  {rows.map((r, ri) => (
                                                    <Box as="tr" key={ri} borderBottom="1px solid" borderColor="paper.200" _hover={{ bg: "paper.50" }}>
                                                      <Box as="td" py={1} px={2} color="ink.800" fontWeight="600">{r.model || "N/A"}</Box>
                                                      <Box as="td" py={1} px={2} color="ink.600">{formatMetric(r.metric) || "N/A"}</Box>
                                                      <Box as="td" py={1} px={2} color="teal.700" fontWeight="700" textAlign="right">
                                                        {typeof r.value === "number" && r.value <= 1 ? `${(r.value * 100).toFixed(1)}%` : String(r.value ?? "N/A")}
                                                      </Box>
                                                    </Box>
                                                  ))}
                                                </Box>
                                              </Box>
                                            </Box>
                                          </Box>
                                        ))}
                                      </VStack>
                                    );
                                  };

                                  return (
                                    <Box key={secKey} bg="paper.50" p={4} border="1px solid" borderColor="paper.300" borderRadius="md">
                                      <Text fontWeight="bold" fontSize="sm" color="teal.800" mb={3} textTransform="uppercase" letterSpacing="wide">
                                        {secKey.replace(/_/g, " ")}
                                      </Text>
                                      {typeof secVal === "object" && !Array.isArray(secVal) ? (
                                        <VStack align="stretch" spacing={3}>
                                          {Object.entries(secVal).map(([k, v]) => {
                                            const label = k.replace(/_/g, " ");
                                            // Special case: reported_numbers gets a table
                                            if (k === "reported_numbers" || k === "reported numbers") {
                                              return (
                                                <Box key={k}>
                                                  <Text fontSize="xs" color="slate.600" fontWeight="700" mb={2} textTransform="uppercase">{label}</Text>
                                                  {renderReportedNumbers(v)}
                                                </Box>
                                              );
                                            }
                                            // Arrays of objects (other than reported_numbers)
                                            if (Array.isArray(v) && v.length > 0 && typeof v[0] === "object") {
                                              return (
                                                <Box key={k}>
                                                  <Text fontSize="xs" color="slate.600" fontWeight="700" mb={1.5} textTransform="uppercase">{label}</Text>
                                                  <VStack align="stretch" spacing={1.5} pl={1}>
                                                    {v.map((item, vi) => (
                                                      <Box key={vi} bg="white" p={2} borderRadius="sm" border="1px solid" borderColor="paper.200">
                                                        {Object.entries(item).map(([ik, iv]) => (
                                                          <Text key={ik} fontSize="xs" color="ink.700">
                                                            <Text as="span" fontWeight="600" color="ink.800">{ik.replace(/_/g, " ")}: </Text>
                                                            {String(iv)}
                                                          </Text>
                                                        ))}
                                                      </Box>
                                                    ))}
                                                  </VStack>
                                                </Box>
                                              );
                                            }
                                            return (
                                              <Box key={k}>
                                                <Text fontSize="xs" color="slate.600" fontWeight="700" mb={1} textTransform="uppercase">{label}</Text>
                                                {renderValue(v)}
                                              </Box>
                                            );
                                          })}
                                        </VStack>
                                      ) : (
                                        renderValue(secVal)
                                      )}
                                    </Box>
                                  );
                                })}
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

            {selectedSection === "technical_plan" && s.technical_plan && (() => {
              const tp = s.technical_plan;
              const stack = tp.recommended_stack || {};
              const milestones = tp.milestones || [];
              const deliverables = tp.deliverables || [];
              const risks = tp.risks || [];
              return (
                <VStack align="stretch" spacing={4}>
                  {tp.novelty_assessment && (
                    <Box p={4} bg="green.50" borderRadius="md" border="1px solid" borderColor="green.200">
                      <Text fontSize="xs" color="green.700" fontWeight="bold" mb={1}>NOVELTY ASSESSMENT</Text>
                      <Text fontSize="sm" color="ink.800">{tp.novelty_assessment}</Text>
                    </Box>
                  )}
                  {tp.differentiation_strategy && (
                    <Box p={4} bg="blue.50" borderRadius="md" border="1px solid" borderColor="blue.200">
                      <Text fontSize="xs" color="blue.700" fontWeight="bold" mb={1}>DIFFERENTIATION STRATEGY</Text>
                      <Text fontSize="sm" color="ink.800">{tp.differentiation_strategy}</Text>
                    </Box>
                  )}
                  {Object.keys(stack).length > 0 && (
                    <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                      <Text fontSize="xs" color="slate.500" fontWeight="bold" mb={2}>RECOMMENDED STACK</Text>
                      {stack.core_technologies && (
                        <HStack spacing={1.5} mb={2} wrap="wrap">
                          {(Array.isArray(stack.core_technologies) ? stack.core_technologies : [stack.core_technologies]).map((t) => (
                            <Badge key={t} colorScheme="purple" fontSize="xs" px={2} py={0.5} borderRadius="sm">{t}</Badge>
                          ))}
                        </HStack>
                      )}
                      {stack.frameworks && (
                        <Box mb={2}>
                          <Text fontSize="xs" color="ink.600" fontWeight="bold" mb={1}>Frameworks:</Text>
                          <HStack spacing={1.5} wrap="wrap">
                            {(Array.isArray(stack.frameworks) ? stack.frameworks : [stack.frameworks]).map((f) => (
                              <Badge key={f} colorScheme="teal" fontSize="xs" px={2} py={0.5} borderRadius="sm">{f}</Badge>
                            ))}
                          </HStack>
                        </Box>
                      )}
                      {stack.rationale && <Text fontSize="xs" color="ink.600" mt={1}><b>Rationale:</b> {stack.rationale}</Text>}
                    </Box>
                  )}
                  {tp.architecture_overview && (
                    <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                      <Text fontSize="xs" color="slate.500" fontWeight="bold" mb={2}>ARCHITECTURE OVERVIEW</Text>
                      <Text fontSize="sm" color="ink.800" whiteSpace="pre-wrap">{tp.architecture_overview}</Text>
                    </Box>
                  )}
                  {milestones.length > 0 && (
                    <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                      <Text fontSize="xs" color="slate.500" fontWeight="bold" mb={3}>MILESTONES ({milestones.length})</Text>
                      <VStack align="stretch" spacing={3}>
                        {milestones.map((m, idx) => {
                          const title = typeof m === "string" ? m : (m.title || m.name || `Milestone ${idx + 1}`);
                          const desc = typeof m === "object" ? (m.description || "") : "";
                          const duration = typeof m === "object" ? (m.duration || m.timeline || "") : "";
                          return (
                            <HStack key={idx} align="start" spacing={3}>
                              <Badge bg="gold.100" color="gold.800" fontSize="xs" borderRadius="full" minW="24px" textAlign="center" mt="2px">
                                {idx + 1}
                              </Badge>
                              <Box>
                                <Text fontSize="sm" fontWeight="600" color="ink.900">{title}</Text>
                                {desc && <Text fontSize="xs" color="ink.600" mt={0.5}>{desc}</Text>}
                                {duration && <Text fontSize="xs" color="slate.500" mt={0.5}>⏱ {duration}</Text>}
                              </Box>
                            </HStack>
                          );
                        })}
                      </VStack>
                    </Box>
                  )}
                  {deliverables.length > 0 && (
                    <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                      <Text fontSize="xs" color="slate.500" fontWeight="bold" mb={2}>DELIVERABLES</Text>
                      <VStack align="stretch" spacing={1}>
                        {deliverables.map((d, idx) => (
                          <Text key={idx} fontSize="sm" color="ink.800">• {typeof d === "string" ? d : (d.name || d.description || JSON.stringify(d))}</Text>
                        ))}
                      </VStack>
                    </Box>
                  )}
                  {risks.length > 0 && (
                    <Box p={4} bg="orange.50" borderRadius="md" border="1px solid" borderColor="orange.200">
                      <Text fontSize="xs" color="orange.700" fontWeight="bold" mb={2}>RISKS</Text>
                      <VStack align="stretch" spacing={1}>
                        {risks.map((r, idx) => (
                          <Text key={idx} fontSize="sm" color="ink.800">⚠ {typeof r === "string" ? r : (r.description || r.risk || JSON.stringify(r))}</Text>
                        ))}
                      </VStack>
                    </Box>
                  )}
                </VStack>
              );
            })()}

            {selectedSection === "teaching_plan" && s.teaching_plan && (() => {
              const plan = s.teaching_plan;
              const modules = plan.modules || [];
              const objectives = plan.learning_objectives || [];
              const prereqs = plan.prerequisites || [];
              const frontier = plan.frontier_topics || [];
              return (
                <VStack align="stretch" spacing={4}>
                  <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                    <Text fontSize="lg" fontWeight="700" color="ink.900" mb={1}>{plan.course_title || "Untitled Course"}</Text>
                    <HStack spacing={2} wrap="wrap">
                      {plan.target_audience && <Badge colorScheme="blue" fontSize="xs">{plan.target_audience}</Badge>}
                      {plan.suggested_duration && <Badge colorScheme="green" fontSize="xs">⏱ {plan.suggested_duration}</Badge>}
                    </HStack>
                  </Box>
                  {objectives.length > 0 && (
                    <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                      <Text fontSize="xs" color="slate.500" fontWeight="bold" mb={2}>LEARNING OBJECTIVES</Text>
                      <VStack align="stretch" spacing={1.5}>
                        {objectives.map((obj, idx) => (
                          <HStack key={idx} align="start" spacing={2}>
                            <Text color="green.500" fontSize="sm" mt="1px">✓</Text>
                            <Text fontSize="sm" color="ink.800">{obj}</Text>
                          </HStack>
                        ))}
                      </VStack>
                    </Box>
                  )}
                  {prereqs.length > 0 && (
                    <Box p={4} bg="paper.100" borderRadius="md" border="1px solid" borderColor="paper.300">
                      <Text fontSize="xs" color="slate.500" fontWeight="bold" mb={2}>PREREQUISITES</Text>
                      <VStack align="stretch" spacing={1}>
                        {prereqs.map((pr, idx) => (
                          <Text key={idx} fontSize="sm" color="ink.700">• {pr}</Text>
                        ))}
                      </VStack>
                    </Box>
                  )}
                  {modules.length > 0 && (
                    <Box>
                      <Text fontSize="xs" color="slate.500" fontWeight="bold" mb={3}>MODULES ({modules.length})</Text>
                      <Accordion allowMultiple>
                        {modules.map((m, idx) => (
                          <AccordionItem key={idx} border="1px solid" borderColor="paper.300" borderRadius="md" mb={2} overflow="hidden">
                            <AccordionButton px={4} py={3} _hover={{ bg: "paper.100" }}>
                              <HStack flex="1" spacing={2}>
                                <Badge bg="gold.100" color="gold.800" fontSize="xs" borderRadius="full" minW="24px" textAlign="center">{idx + 1}</Badge>
                                <Text fontSize="sm" fontWeight="600" color="ink.900" textAlign="left">{m.title || "Untitled Module"}</Text>
                              </HStack>
                              <AccordionIcon />
                            </AccordionButton>
                            <AccordionPanel px={4} pb={4} bg="white">
                              {m.description && <Text fontSize="sm" color="ink.700" mb={2}>{m.description}</Text>}
                              {m.problem_addressed && (
                                <Box mb={2}><Text fontSize="xs" color="slate.600"><b>Problem:</b> {m.problem_addressed}</Text></Box>
                              )}
                              {m.solution_approach && (
                                <Box mb={2}><Text fontSize="xs" color="slate.600"><b>Approach:</b> {m.solution_approach}</Text></Box>
                              )}
                              {m.based_on_papers && (
                                <HStack spacing={1} wrap="wrap" mt={1}>
                                  <Text fontSize="xs" color="slate.500" fontWeight="bold">Papers:</Text>
                                  {(Array.isArray(m.based_on_papers) ? m.based_on_papers : [m.based_on_papers]).map((paper, pi) => (
                                    <Badge key={pi} fontSize="xs" colorScheme="purple" variant="subtle">{paper}</Badge>
                                  ))}
                                </HStack>
                              )}
                            </AccordionPanel>
                          </AccordionItem>
                        ))}
                      </Accordion>
                    </Box>
                  )}
                  {frontier.length > 0 && (
                    <Box p={4} bg="purple.50" borderRadius="md" border="1px solid" borderColor="purple.200">
                      <Text fontSize="xs" color="purple.700" fontWeight="bold" mb={2}>FRONTIER TOPICS ({frontier.length})</Text>
                      <VStack align="stretch" spacing={2}>
                        {frontier.map((ft, idx) => (
                          <Box key={idx}>
                            <Text fontSize="sm" fontWeight="600" color="ink.900">
                              🔬 {typeof ft === "string" ? ft : (ft.topic || ft.title || "Untitled")}
                            </Text>
                            {typeof ft === "object" && (ft.description || ft.relevance) && (
                              <Text fontSize="xs" color="ink.600" mt={0.5}>{ft.description || ft.relevance}</Text>
                            )}
                          </Box>
                        ))}
                      </VStack>
                    </Box>
                  )}
                </VStack>
              );
            })()}

            {selectedSection === "course" && s.course && (() => {
              const course = s.course;
              const modules = course.modules || [];
              const downloads = s.course_downloads || [];
              return (
                <VStack align="stretch" spacing={4}>
                  <Box p={4} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
                    <Text fontSize="lg" fontWeight="700" color="ink.900" mb={1}>{course.course_title || "Generated Course"}</Text>
                    <Text fontSize="xs" color="slate.500" mb={downloads.length > 0 ? 3 : 0}>
                      {modules.length} module(s), {modules.reduce((acc, m) => acc + (m.lessons?.length || 0), 0)} lesson(s)
                    </Text>
                    {downloads.length > 0 && (
                      <Box mt={2} pt={3} borderTop="1px solid" borderColor="paper.200">
                        <Text fontSize="xs" color="teal.700" fontWeight="bold" mb={2}>AVAILABLE DOWNLOADS:</Text>
                        <HStack spacing={2} wrap="wrap">
                          {downloads.map((download, idx) => (
                            <Button
                              key={idx}
                              size="xs"
                              colorScheme="teal"
                              onClick={() => downloadArtifact(download)}
                            >
                              📄 {download.label || `Download Presentation ${idx + 1}`}
                            </Button>
                          ))}
                        </HStack>
                      </Box>
                    )}
                  </Box>
                  <Accordion allowMultiple>
                    {modules.map((mod, mi) => (
                      <AccordionItem key={mi} border="1px solid" borderColor="paper.300" borderRadius="md" mb={3} overflow="hidden">
                        <AccordionButton px={4} py={3} bg="paper.50" _hover={{ bg: "paper.100" }}>
                          <HStack flex="1" spacing={2}>
                            <Badge bg="gold.100" color="gold.800" fontSize="xs" borderRadius="full" minW="28px" textAlign="center">M{mi + 1}</Badge>
                            <Text fontSize="sm" fontWeight="700" color="ink.900" textAlign="left">{mod.module_title || "Untitled Module"}</Text>
                          </HStack>
                          <AccordionIcon />
                        </AccordionButton>
                        <AccordionPanel px={0} pb={0} bg="white">
                          {(mod.lessons || []).map((lesson, li) => (
                            <Accordion key={li} allowToggle>
                              <AccordionItem border="none" borderTop="1px solid" borderColor="paper.200">
                                <AccordionButton px={4} py={2.5} _hover={{ bg: "paper.50" }}>
                                  <HStack flex="1" spacing={2}>
                                    <Text fontSize="xs" color="slate.500" fontFamily="mono">L{li + 1}</Text>
                                    <Text fontSize="sm" fontWeight="600" color="ink.800" textAlign="left">{lesson.lesson_title || "Untitled Lesson"}</Text>
                                  </HStack>
                                  <AccordionIcon />
                                </AccordionButton>
                                <AccordionPanel px={4} pb={4}>
                                  <VStack align="stretch" spacing={3}>
                                    {(lesson.sections || []).map((sec, si) => (
                                      <Box key={si} p={3} bg="paper.50" borderRadius="md" border="1px solid" borderColor="paper.200">
                                        <Text fontSize="sm" fontWeight="600" color="teal.800" mb={1.5}>{sec.topic || "Untitled Section"}</Text>
                                        {sec.explanation && (
                                          <Text fontSize="xs" color="ink.700" mb={2} whiteSpace="pre-wrap" lineHeight="1.6">{sec.explanation}</Text>
                                        )}
                                        {sec.example_or_evidence && (
                                          <Box bg="blue.50" p={2} borderRadius="sm" mb={2} border="1px solid" borderColor="blue.100">
                                            <Text fontSize="xs" color="blue.800"><b>Example / Evidence:</b> {sec.example_or_evidence}</Text>
                                          </Box>
                                        )}
                                        {sec.key_terms && sec.key_terms.length > 0 && (
                                          <HStack spacing={1} wrap="wrap">
                                            {(Array.isArray(sec.key_terms) ? sec.key_terms : [sec.key_terms]).map((term, ti) => (
                                              <Badge key={ti} fontSize="xs" colorScheme="gray" variant="subtle">{term}</Badge>
                                            ))}
                                          </HStack>
                                        )}
                                      </Box>
                                    ))}
                                  </VStack>
                                </AccordionPanel>
                              </AccordionItem>
                            </Accordion>
                          ))}
                        </AccordionPanel>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </VStack>
              );
            })()}

            {selectedSection === "experiments" && s.experiments && (() => {
              const expData = s.experiments;
              const exps = expData.experiments || [];
              const labDownloads = s.lab_downloads || [];
              return (
                <VStack align="stretch" spacing={4}>
                  {labDownloads.length > 0 && (
                    <Box p={3} bg="purple.50" borderRadius="md" border="1px solid" borderColor="purple.200">
                      <Text fontSize="xs" color="purple.800" fontWeight="bold" mb={2}>LAB NOTEBOOK DOWNLOADS:</Text>
                      <HStack spacing={2} wrap="wrap">
                        {labDownloads.map((download, idx) => (
                          <Button
                            key={idx}
                            size="xs"
                            colorScheme="purple"
                            onClick={() => downloadArtifact(download)}
                          >
                            📓 {download.label || `Download Notebook ${idx + 1}`}
                          </Button>
                        ))}
                      </HStack>
                    </Box>
                  )}
                  <Text fontSize="md" fontWeight="600" color="ink.800" mb={1}>
                    {exps.length} Suggested Experiment{exps.length !== 1 ? "s" : ""}
                  </Text>
                  {exps.map((exp, idx) => (
                    <Box key={idx} p={4} bg="white" borderRadius="md" border="1.5px solid" borderColor="paper.300" boxShadow="sm">
                      <HStack justify="space-between" mb={2} align="center">
                        <Badge bg="gold.100" color="gold.800" fontSize="xs" borderRadius="full" px={2.5}>
                          Experiment {idx + 1}
                        </Badge>
                        {exp.difficulty && <Badge colorScheme="purple" fontSize="xs">{exp.difficulty}</Badge>}
                      </HStack>
                      <Text fontWeight="700" fontSize="sm" color="ink.900" mb={2}>{exp.title || "Untitled Experiment"}</Text>
                      {exp.hypothesis && (
                        <Box bg="blue.50" p={2.5} borderRadius="md" mb={2} border="1px solid" borderColor="blue.100">
                          <Text fontSize="xs" color="blue.800"><b>Hypothesis:</b> {exp.hypothesis}</Text>
                        </Box>
                      )}
                      {exp.gap_addressed && (
                        <Text fontSize="xs" color="ink.600" mb={2}><b>Gap Addressed:</b> {exp.gap_addressed}</Text>
                      )}
                      {exp.dataset && (
                        <Box bg="paper.50" p={2.5} borderRadius="md" mb={2} border="1px solid" borderColor="paper.200">
                          <Text fontSize="xs" color="slate.600" fontWeight="bold" mb={1}>DATASET</Text>
                          {typeof exp.dataset === "object" ? (
                            <VStack align="stretch" spacing={1}>
                              {exp.dataset.name && <Text fontSize="xs" color="ink.800"><b>Name:</b> {exp.dataset.name}</Text>}
                              {exp.dataset.source && <Text fontSize="xs" color="ink.700"><b>Source:</b> {exp.dataset.source}</Text>}
                              {exp.dataset.notes && <Text fontSize="xs" color="ink.700"><b>Notes:</b> {exp.dataset.notes}</Text>}
                              {Object.entries(exp.dataset).map(([dk, dv]) => {
                                if (["name", "source", "notes", "grounded"].includes(dk)) return null;
                                return <Text key={dk} fontSize="xs" color="ink.700"><b>{dk.replace(/_/g, " ")}:</b> {String(dv)}</Text>;
                              })}
                            </VStack>
                          ) : (
                            <Text fontSize="xs" color="ink.700">{String(exp.dataset)}</Text>
                          )}
                        </Box>
                      )}
                      {exp.metrics && (
                        <Box mb={2}>
                          <Text fontSize="xs" color="ink.600" fontWeight="bold" mb={1}>Metrics:</Text>
                          <HStack spacing={1.5} wrap="wrap">
                            {(Array.isArray(exp.metrics) ? exp.metrics : [exp.metrics]).map((m, mi) => {
                              const label = typeof m === "object" ? (m.name || m.metric || JSON.stringify(m)) : String(m);
                              return <Badge key={mi} fontSize="xs" colorScheme="green" px={2} py={0.5} borderRadius="sm">{label}</Badge>;
                            })}
                          </HStack>
                        </Box>
                      )}
                      {exp.baselines && (
                        <Box mb={2}>
                          <Text fontSize="xs" color="ink.600" fontWeight="bold" mb={1}>Baselines:</Text>
                          <HStack spacing={1.5} wrap="wrap">
                            {(Array.isArray(exp.baselines) ? exp.baselines : [exp.baselines]).map((b, bi) => {
                              const label = typeof b === "object" ? (b.name || b.baseline || JSON.stringify(b)) : String(b);
                              return <Badge key={bi} fontSize="xs" colorScheme="orange" px={2} py={0.5} borderRadius="sm">{label}</Badge>;
                            })}
                          </HStack>
                        </Box>
                      )}
                      {exp.protocol && (
                        <Box mt={2} p={2.5} bg="paper.100" borderRadius="md" border="1px solid" borderColor="paper.300">
                          <Text fontSize="xs" color="slate.600" fontWeight="bold" mb={1}>PROTOCOL</Text>
                          {Array.isArray(exp.protocol) ? (
                            <VStack align="stretch" spacing={1}>
                              {exp.protocol.map((step, si) => (
                                <HStack key={si} align="start" spacing={2}>
                                  <Text fontSize="xs" color="gold.800" fontWeight="bold" minW="18px">{si + 1}.</Text>
                                  <Text fontSize="xs" color="ink.800">{typeof step === "object" ? (step.step || step.description || JSON.stringify(step)) : String(step)}</Text>
                                </HStack>
                              ))}
                            </VStack>
                          ) : typeof exp.protocol === "object" ? (
                            <VStack align="stretch" spacing={1}>
                              {Object.entries(exp.protocol).map(([pk, pv]) => (
                                <Text key={pk} fontSize="xs" color="ink.700">
                                  <b>{pk.replace(/_/g, " ")}:</b> {typeof pv === "object" ? JSON.stringify(pv) : String(pv)}
                                </Text>
                              ))}
                            </VStack>
                          ) : (
                            <Text fontSize="xs" color="ink.700" whiteSpace="pre-wrap">{String(exp.protocol)}</Text>
                          )}
                        </Box>
                      )}
                      {exp.expected_outcome && (
                        <Box mt={2} p={2} bg="green.50" borderRadius="sm" border="1px solid" borderColor="green.100">
                          <Text fontSize="xs" color="green.800"><b>Expected Outcome:</b> {exp.expected_outcome}</Text>
                        </Box>
                      )}
                    </Box>
                  ))}
                </VStack>
              );
            })()}
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </Box>
  );
}
