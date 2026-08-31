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
  IconButton,
  Tooltip,
  useColorModeValue,
  Flex
} from "@chakra-ui/react";
import { Icon } from "@chakra-ui/react"; 
import { FiBookOpen, FiGitBranch, FiAlertCircle, FiCpu, FiUsers, FiLayers, FiCircle, FiChevronRight, FiCode, FiDownload, FiArrowDown, FiCheckCircle, FiPlayCircle, FiFileText } from "react-icons/fi";
import { FaLightbulb, FaFlask, FaLaptopCode } from "react-icons/fa";

const LEDGER_ICONS = {
  idea: FaLightbulb,
  literature: FiBookOpen,
  similar_projects: FiGitBranch,
  gaps: FiAlertCircle,
  technical_plan: FiCpu,
  teaching_plan: FiUsers,
  course: FiLayers,
  practical_exercises: FaLaptopCode,
  experiments: FaFlask,
};

function slugify(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function generateClientSideNotebookDownload(exercise) {
  const notebook = {
    cells: [
      {
        cell_type: "markdown",
        metadata: {},
        source: [
          `# ${exercise.title}\n`,
          `**Difficulty:** ${(exercise.difficulty || "intermediate").toUpperCase()} | **Module:** ${exercise.basedOnModule || 'N/A'}\n\n`,
          `## Objective\n${exercise.objective}\n\n`,
          `## Instructions & Context\n${exercise.instructions}\n`
        ]
      },
      {
        cell_type: "markdown",
        metadata: {},
        source: [
          `## Topics / Concepts Covered\n`,
          ...(exercise.topics || []).map(t => `- ${t}\n`),
          `\n## Expected Outcomes\n${typeof exercise.outcomes === 'string' ? exercise.outcomes : JSON.stringify(exercise.outcomes)}\n`
        ]
      },
      {
        cell_type: "code",
        execution_count: null,
        metadata: {},
        outputs: [],
        source: [
          exercise.starterCode || 
          `# ${exercise.title} - Starter Code\n# Complete the exercise based on the instructions above\n\ndef main():\n    print("Starting exercise: ${exercise.title}")\n\nif __name__ == "__main__":\n    main()`
        ]
      }
    ],
    metadata: {
      language_info: { name: "python" }
    },
    nbformat: 4,
    nbformat_minor: 2
  };

  const blob = new Blob([JSON.stringify(notebook, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${slugify(exercise.title || "practical_exercise")}.ipynb`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function handleDownloadNotebook(downloadItem, exercise) {
  if (downloadItem && downloadItem.url) {
    try {
      await downloadArtifact(downloadItem);
      return;
    } catch (e) {
      console.warn("Backend notebook fetch failed, falling back to client-side download", e);
    }
  }
  generateClientSideNotebookDownload(exercise);
}

function extractPracticalExercises(state) {
  const s = state || {};
  const exercises = [];

  const addEx = (raw, moduleTitle, lessonTitle, defaultIdx) => {
    if (!raw || typeof raw !== "object") return;
    const title = String(raw.exercise_title || raw.title || (lessonTitle ? `Practical Lab: ${lessonTitle}` : `Practical Exercise ${defaultIdx + 1}`));
    const objective = String(raw.learning_objective || raw.objective || raw.objectives || "Apply machine learning and software concepts to hands-on practical exercises.");
    const instructions = String(raw.instructions || raw.description || raw.context || "Follow the step-by-step practical guide to complete the exercise.");
    const difficulty = String(raw.difficulty || "intermediate");
    const format = String(raw.format || "notebook");
    const hints = (Array.isArray(raw.hints) ? raw.hints : []).map(h => String(h));
    const repo = raw.based_on_repo || null;
    const modTitle = String(raw.based_on_module || moduleTitle || "Practical Work Module");
    const lesTitle = String(raw.based_on_lesson || lessonTitle || "Practical Work Lesson");

    let codePlan = [];
    if (Array.isArray(raw.code_plan) && raw.code_plan.length > 0) {
      codePlan = raw.code_plan.map((cp, idx) => ({
        step: cp.step || idx + 1,
        goal: String(cp.goal || cp.description || `Step ${idx + 1}`),
        uses: (Array.isArray(cp.uses) ? cp.uses : (cp.uses ? [cp.uses] : [])).map(u => String(u)),
        produces: (Array.isArray(cp.produces) ? cp.produces : (cp.produces ? [cp.produces] : [])).map(p => String(p))
      }));
    } else {
      codePlan = [
        {
          step: 1,
          goal: `Data Ingestion & Environment Setup for ${title}`,
          uses: ["Raw Dataset / API Endpoint"],
          produces: ["data_loader", "preprocessed_dataset"]
        },
        {
          step: 2,
          goal: `Model Architecture & Baseline Implementation`,
          uses: ["preprocessed_dataset"],
          produces: ["model_pipeline", "trainer_object"]
        },
        {
          step: 3,
          goal: `Cross-Domain Evaluation & Model Benchmarking`,
          uses: ["model_pipeline"],
          produces: ["predictions", "evaluation_metrics"]
        },
        {
          step: 4,
          goal: `Statistical Significance Analysis & Visualization`,
          uses: ["evaluation_metrics"],
          produces: ["statistical_summary", "performance_plots"]
        }
      ];
    }

    let topics = (raw.topics || []).map(t => String(t));
    if (!topics.length && codePlan.length) {
      topics = codePlan.map(sp => sp.goal);
    }
    if (!topics.length) {
      topics = [lesTitle, modTitle];
    }

    let outcomes = raw.expected_outcomes || raw.expected_outcome || raw.deliverables;
    if (!outcomes) {
      const producedVars = codePlan.flatMap(sp => sp.produces || []).filter(Boolean);
      if (producedVars.length > 0) {
        outcomes = `Artifacts & Variables Produced: ${producedVars.join(", ")}`;
      } else {
        outcomes = "Verified pipeline execution with computed accuracy, F1-score metrics, and downloadable Jupyter notebook.";
      }
    }

    const labDownloads = Array.isArray(s.lab_downloads) ? s.lab_downloads : [];
    let notebookDownload = labDownloads.find(d => {
      if (!d) return false;
      const dLabel = d.label ? String(d.label).toLowerCase() : "";
      const dFilename = d.filename ? String(d.filename).toLowerCase() : "";
      const titleSlug = slugify(title);
      const titleLower = String(title).toLowerCase();
      const lesLower = String(lesTitle).toLowerCase();
      return (
        (dLabel && titleLower && dLabel.includes(titleLower)) ||
        (dLabel && lesLower && dLabel.includes(lesLower)) ||
        (dFilename && titleSlug && dFilename.includes(titleSlug))
      );
    });

    if (!notebookDownload && (raw.notebook_files || raw.starter_code || format === "notebook")) {
      const fname = `${slugify(title)}.ipynb`;
      notebookDownload = {
        label: `Download Notebook: ${title}`,
        filename: fname,
        url: `/chat/lab-download/${fname}`,
        starter_code: raw.starter_code,
        solution_code: raw.solution_code
      };
    }

    exercises.push({
      id: `ex_${exercises.length + 1}`,
      title,
      objective,
      instructions,
      difficulty,
      format,
      hints,
      repo,
      basedOnModule: modTitle,
      basedOnLesson: lesTitle,
      codePlan,
      topics,
      outcomes,
      notebookDownload,
      starterCode: raw.starter_code || null,
      solutionCode: raw.solution_code || null,
      debugMode: Boolean(raw.debug_mode),
      debugHint: raw.debug_hint || null,
      raw
    });
  };

  let rawLabs = s.lab_exercises || s.practical_exercises;
  let labModules = [];
  if (Array.isArray(rawLabs)) {
    labModules = rawLabs;
  } else if (rawLabs && typeof rawLabs === "object") {
    labModules = Array.isArray(rawLabs.modules) ? rawLabs.modules : [rawLabs];
  }

  labModules.forEach((item, idx) => {
    if (!item || typeof item !== "object") return;
    if (item.module_title && Array.isArray(item.lessons)) {
      item.lessons.forEach((les, lidx) => {
        if (!les || typeof les !== "object") return;
        const labData = les.lab || les;
        addEx(
          { ...labData, notebook_files: les.notebook_files || labData.notebook_files },
          item.module_title,
          les.lesson_title || labData.based_on_lesson,
          exercises.length
        );
      });
    } else if (item.lab && typeof item.lab === "object") {
      addEx(
        { ...item.lab, notebook_files: item.notebook_files || item.lab.notebook_files },
        item.module_title,
        item.lesson_title,
        exercises.length
      );
    } else if (item.exercise_title || item.title || item.instructions) {
      addEx(item, item.based_on_module, item.based_on_lesson, exercises.length);
    }
  });

  if (exercises.length === 0 && s.course && Array.isArray(s.course.modules)) {
    s.course.modules.forEach((mod) => {
      if (!mod || typeof mod !== "object") return;
      (mod.lessons || []).forEach((les) => {
        if (!les || typeof les !== "object") return;
        const labObj = les.lab || les.practical_exercise || les.exercise || {
          exercise_title: `Practical Lab: ${les.lesson_title || mod.module_title || "Lesson"}`,
          learning_objective: `Implement hands-on code to test and apply ${les.lesson_title || mod.module_title || "lesson concepts"}.`,
          instructions: `In this exercise, you will build a practical pipeline based on the lesson "${les.lesson_title || mod.module_title}". Follow the step-by-step plan in the organigram below to complete the implementation.`,
          difficulty: "intermediate",
          format: "notebook",
          code_plan: (les.sections || []).map((sec, si) => ({
            step: si + 1,
            goal: sec.topic || `Implement section ${si + 1}`,
            uses: si === 0 ? ["lesson_dataset"] : [`output_step_${si}`],
            produces: [`output_step_${si + 1}`]
          }))
        };
        addEx(labObj, mod.module_title, les.lesson_title, exercises.length);
      });
    });
  }

  return exercises;
}

function ExerciseOrganigram({ codePlan, exerciseTitle }) {
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [viewMode, setViewMode] = useState("organigram");

  const bgNode = useColorModeValue("white", "gray.800");
  const bgNodeActive = useColorModeValue("paper.100", "gray.700");
  const borderNode = useColorModeValue("paper.300", "gray.600");
  const textTitle = useColorModeValue("ink.900", "gray.100");

  if (!codePlan || codePlan.length === 0) {
    return (
      <Box p={4} bg="paper.100" borderRadius="md">
        <Text fontSize="xs" color="slate.500">No step plan available for this organigram.</Text>
      </Box>
    );
  }

  const activeStep = codePlan[activeStepIndex] || codePlan[0];

  return (
    <Box p={4} bg="paper.100" borderRadius="xl" border="1.5px solid" borderColor="paper.300" boxShadow="sm">
      <HStack justify="space-between" align="center" mb={3}>
        <HStack spacing={2}>
          <Icon as={FiGitBranch} color="gold.700" boxSize={4} />
          <Text fontSize="xs" fontWeight="700" color="gold.800" letterSpacing="wide" textTransform="uppercase">
            EXERCISE PLAN ORGANIGRAM (FLOW DIAGRAM)
          </Text>
        </HStack>
        <HStack spacing={1}>
          <Badge colorScheme="gold" fontSize="10px" borderRadius="full" px={2}>
            {codePlan.length} Stages
          </Badge>
          <Button
            size="xs"
            variant="ghost"
            colorScheme="teal"
            fontSize="10px"
            onClick={() => setViewMode(viewMode === "organigram" ? "compact" : "organigram")}
          >
            {viewMode === "organigram" ? "Compact View" : "Diagram View"}
          </Button>
        </HStack>
      </HStack>

      <Text fontSize="xs" color="slate.600" mb={4}>
        Interactive step-by-step visual progression of tasks, inputs, and output deliverables. Click any node in the organigram to inspect details.
      </Text>

      {viewMode === "organigram" ? (
        <VStack align="stretch" spacing={0} position="relative">
          {codePlan.map((stepItem, idx) => {
            const isSelected = idx === activeStepIndex;
            const isLast = idx === codePlan.length - 1;
            const uses = stepItem.uses || [];
            const produces = stepItem.produces || [];

            return (
              <Box key={idx} position="relative" pb={isLast ? 0 : 4}>
                {!isLast && (
                  <Box
                    position="absolute"
                    left="24px"
                    top="48px"
                    bottom="0"
                    w="2px"
                    bg={isSelected ? "gold.500" : "paper.300"}
                    zIndex={1}
                    transition="all 0.2s"
                  />
                )}

                <HStack align="start" spacing={3} position="relative" zIndex={2}>
                  <Box
                    w="48px"
                    h="48px"
                    borderRadius="full"
                    bg={isSelected ? "gold.500" : "white"}
                    color={isSelected ? "white" : "gold.700"}
                    border="2px solid"
                    borderColor={isSelected ? "gold.600" : "paper.400"}
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                    fontWeight="bold"
                    fontSize="sm"
                    boxShadow={isSelected ? "0 0 0 3px rgba(212,175,55,0.3)" : "sm"}
                    cursor="pointer"
                    onClick={() => setActiveStepIndex(idx)}
                    transition="all 0.2s"
                    _hover={{ transform: "scale(1.08)" }}
                    flexShrink={0}
                  >
                    {stepItem.step || idx + 1}
                  </Box>

                  <Box
                    flex="1"
                    p={3.5}
                    bg={isSelected ? bgNodeActive : bgNode}
                    borderRadius="lg"
                    border="1.5px solid"
                    borderColor={isSelected ? "gold.400" : borderNode}
                    boxShadow={isSelected ? "md" : "xs"}
                    cursor="pointer"
                    onClick={() => setActiveStepIndex(idx)}
                    _hover={{ borderColor: "gold.400", boxShadow: "sm" }}
                    transition="all 0.2s"
                  >
                    <HStack justify="space-between" mb={1.5} align="center">
                      <Text fontSize="xs" fontWeight="700" color={isSelected ? "gold.800" : "slate.500"}>
                        STAGE {stepItem.step || idx + 1}
                      </Text>
                      {isSelected && (
                        <Badge colorScheme="green" fontSize="9px" px={2} borderRadius="full">
                          ACTIVE INSPECTION
                        </Badge>
                      )}
                    </HStack>

                    <Text fontSize="sm" fontWeight="600" color={textTitle} mb={2} lineHeight="short">
                      {stepItem.goal}
                    </Text>

                    <HStack spacing={2} wrap="wrap" pt={1}>
                      {uses.length > 0 && (
                        <HStack spacing={1} bg="blue.50" px={2} py={0.5} borderRadius="md" border="1px solid" borderColor="blue.100">
                          <Text fontSize="10px" color="blue.700" fontWeight="bold"> Uses :</Text>
                          {uses.map((u, ui) => (
                            <Badge key={ui} fontSize="10px" colorScheme="blue" variant="subtle">{u}</Badge>
                          ))}
                        </HStack>
                      )}
                      {produces.length > 0 && (
                        <HStack spacing={1} bg="teal.50" px={2} py={0.5} borderRadius="md" border="1px solid" borderColor="teal.100">
                          <Text fontSize="10px" color="teal.700" fontWeight="bold"> Produces:</Text>
                          {produces.map((p, pi) => (
                            <Badge key={pi} fontSize="10px" colorScheme="teal" variant="subtle">{p}</Badge>
                          ))}
                        </HStack>
                      )}
                    </HStack>
                  </Box>
                </HStack>

                {!isLast && (
                  <Flex justify="center" w="48px" my={1}>
                    <Icon as={FiArrowDown} boxSize={3.5} color={isSelected ? "gold.600" : "paper.400"} />
                  </Flex>
                )}
              </Box>
            );
          })}
        </VStack>
      ) : (
        <VStack align="stretch" spacing={2}>
          {codePlan.map((stepItem, idx) => (
            <HStack key={idx} p={2.5} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300" justify="space-between">
              <HStack spacing={2}>
                <Badge bg="gold.100" color="gold.800" fontSize="xs" borderRadius="full" minW="22px" textAlign="center">
                  S{stepItem.step || idx + 1}
                </Badge>
                <Text fontSize="xs" fontWeight="600" color="ink.800">{stepItem.goal}</Text>
              </HStack>
              {stepItem.produces?.length > 0 && (
                <Badge colorScheme="teal" fontSize="10px">Produces: {stepItem.produces.join(", ")}</Badge>
              )}
            </HStack>
          ))}
        </VStack>
      )}

      {activeStep && (
        <Box mt={4} pt={3} borderTop="1.5px dashed" borderColor="paper.300">
          <Text fontSize="xs" color="slate.600" fontWeight="bold" mb={1.5} textTransform="uppercase">
             Stage {activeStep.step || activeStepIndex + 1} Step Detail:
          </Text>
          <Box p={3} bg="white" borderRadius="md" border="1px solid" borderColor="paper.300">
            <Text fontSize="xs" color="ink.900" fontWeight="600" mb={2}>
              {activeStep.goal}
            </Text>
            <VStack align="stretch" spacing={1.5} fontSize="xs">
              {activeStep.uses?.length > 0 && (
                <Text color="slate.600">
                  <b>Required Inputs:</b> {activeStep.uses.join(", ")}
                </Text>
              )}
              {activeStep.produces?.length > 0 && (
                <Text color="teal.700">
                  <b>Generated Deliverables / Variables:</b> {activeStep.produces.join(", ")}
                </Text>
              )}
            </VStack>
          </Box>
        </Box>
      )}
    </Box>
  );
}
function LedgerRow({ id, label, detail, done, onClick }) {
  const RowIcon = LEDGER_ICONS[id] || FiCircle;
  const bgRow = useColorModeValue("paper.100", "gray.800");
  const textPrimary = useColorModeValue("ink.900", "gray.100");
  const textSecondary = useColorModeValue("ink.500", "gray.400");

  return (
    <HStack align="start" spacing={3} py={3} px={3} mb={2} borderRadius="14px"
      bg={done ? bgRow : "transparent"}
      boxShadow={done ? "0px 2px 8px rgba(30,25,17,0.06)" : "none"}
      cursor={done ? "pointer" : "default"}
      _hover={done ? { boxShadow: "0px 4px 14px rgba(30,25,17,0.10)" } : {}}
      onClick={done ? onClick : undefined}
      transition="all 0.15s">
      <Box minW="28px" pt="1px" display="flex" justifyContent="center">
        <Icon as={RowIcon} boxSize={4} color={done ? "gold.600" : "paper.300"} />
      </Box>
      <Box flex="1">
        <Text fontSize="sm" fontWeight="600" color={done ? textPrimary : textSecondary}>
          {label}
        </Text>
        {detail && (
          <Text fontSize="xs" color={textSecondary} mt="1px">
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
export default function Sidebar({ state, isCollapsed = false, onToggleCollapse }) {
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

  const practicalExercises = extractPracticalExercises(s);
  const practicalExercisesCount = practicalExercises.length;

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
      id: "practical_exercises",
      label: "Practical Exercises",
      detail: practicalExercisesCount ? `${practicalExercisesCount} exercise(s)` : (s.lab_exercises ? "Generated" : "Not generated"),
      done: practicalExercisesCount > 0,
    },
    {
      id: "experiments",
      label: "Experiments",
      detail: experimentsCount ? `${experimentsCount} experiment(s)` : "Not generated",
      done: experimentsCount > 0,
    },
  ];

  const bgSidebar = useColorModeValue("paper.50", "gray.900");

  return (
    <Box
      w={isCollapsed ? "0px" : `${sidebarWidth}px`}
      flexShrink={0}
      bg={bgSidebar}
      boxShadow={isCollapsed ? "none" : "-4px 0px 24px rgba(30,25,17,0.06)"}
      p={isCollapsed ? 0 : 5}
      opacity={isCollapsed ? 0 : 1}
      overflowX="hidden"
      overflowY={isCollapsed ? "hidden" : "auto"}
      position="relative"
      userSelect={isResizing ? "none" : "auto"}
      transition={isResizing ? "none" : "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)"}
    >
      {/* Resizable Drag Handle */}
      {!isCollapsed && (
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
      )}

      <HStack justify="space-between" align="center" mb={4}>
        <Text fontFamily="heading" fontSize="xxs" fontWeight="bold" color="gold.700" letterSpacing="wide">
          RESEARCH LEDGER
        </Text>
        {onToggleCollapse && (
          <Tooltip label="Collapse right sidebar" placement="bottom-end">
            <IconButton
              icon={<FiChevronRight />}
              size="xs"
              variant="ghost"
              color="slate.500"
              _hover={{ bg: "paper.200", color: "ink.900" }}
              aria-label="Collapse right sidebar"
              onClick={onToggleCollapse}
            />
          </Tooltip>
        )}
      </HStack>

      <VStack align="stretch" spacing={0} >
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
                        <Badge colorScheme="purple" px={3} py={1} borderRadius="md" color="white" bg="gold.700"  fontSize="xs" fontWeight="bold">
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
                            <Badge key={sec} fontSize="xs" px={2} py={0.5} bg="paper.300"  colorScheme="teal" borderRadius="sm">
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

            {selectedSection === "practical_exercises" && (() => {
              const practicalExercisesList = extractPracticalExercises(s);
              const labDownloads = s.lab_downloads || [];

              return (
                <VStack align="stretch" spacing={5}>
                  {/* Header Overview Card */}
                  <Box p={5} bg="white" borderRadius="xl" border="1.5px solid" borderColor="paper.300" boxShadow="sm">
                    <HStack justify="space-between" align="start" mb={2}>
                      <Box>
                        <Text fontSize="lg" fontWeight="700" color="ink.900" lineHeight="tight">
                          Practical Exercises & Labs
                        </Text>
                        <Text fontSize="xs" color="slate.600" mt={1}>
                          Hands-on coding exercises, notebook scaffolds, and interactive organigram plans built from literature and similar project repos.
                        </Text>
                      </Box>
                      <Badge colorScheme="purple" fontSize="xs" px={3} py={1} borderRadius="full">
                        {practicalExercisesList.length} Exercise{practicalExercisesList.length !== 1 ? "s" : ""} Available
                      </Badge>
                    </HStack>

                    {/* Global Notebook Downloads Button Header if available */}
                    {labDownloads.length > 0 && (
                      <Box mt={3} pt={3} borderTop="1px solid" borderColor="paper.200">
                        <Text fontSize="xs" color="teal.700" fontWeight="bold" mb={2} textTransform="uppercase">
                         AVAILABLE JUPYTER NOTEBOOKS:
                        </Text>
                        <HStack spacing={2} wrap="wrap">
                          {labDownloads.map((dl, idx) => (
                            <Button
                              key={idx}
                              size="xs"
                              colorScheme="teal"
                              leftIcon={<Icon as={FiDownload} />}
                              onClick={() => downloadArtifact(dl)}
                            >
                              {dl.label || `Download Notebook ${idx + 1}`}
                            </Button>
                          ))}
                        </HStack>
                      </Box>
                    )}
                  </Box>

                  {/* Exercises List Accordion / Card View */}
                  {practicalExercisesList.length === 0 ? (
                    <Box p={6} bg="white" borderRadius="lg" border="1px solid" borderColor="paper.300" textAlign="center">
                      <Icon as={FaLaptopCode} boxSize={8} color="gold.500" mb={2} />
                      <Text fontSize="sm" fontWeight="bold" color="ink.800" mb={1}>
                        No Practical Exercises Generated Yet
                      </Text>
                      <Text fontSize="xs" color="slate.500" maxW="400px" mx="auto" mb={4}>
                        Ask the assistant to "generate practical exercises", "build lab exercises", or "create notebooks" to generate hands-on exercises tailored to your project idea!
                      </Text>
                    </Box>
                  ) : (
                    <Accordion allowMultiple defaultIndex={[0]}>
                      {practicalExercisesList.map((ex, idx) => {
                        return (
                          <AccordionItem
                            key={ex.id || idx}
                            border="1.5px solid"
                            borderColor="paper.300"
                            borderRadius="xl"
                            mb={4}
                            overflow="hidden"
                            bg="white"
                            boxShadow="sm"
                          >
                            <AccordionButton px={5} py={4} bg="paper.50" _hover={{ bg: "paper.100" }}>
                              <HStack flex="1" spacing={3} align="center">
                                <Badge bg="gold.500" color="white" fontSize="xs" borderRadius="full" px={2.5} py={0.5}>
                                  EX {idx + 1}
                                </Badge>
                                <Box textAlign="left">
                                  <Text fontSize="md" fontWeight="700" color="ink.900" lineHeight="short">
                                    {ex.title}
                                  </Text>
                                  <HStack spacing={2} mt={1} wrap="wrap">
                                    {ex.difficulty && (
                                      <Badge
                                        colorScheme={ex.difficulty === "beginner" ? "green" : ex.difficulty === "advanced" ? "red" : "purple"}
                                        fontSize="10px"
                                        borderRadius="sm"
                                      >
                                        {ex.difficulty.toUpperCase()}
                                      </Badge>
                                    )}
                                    {ex.format && (
                                      <Badge colorScheme="blue" fontSize="10px" borderRadius="sm">
                                        {ex.format.toUpperCase()}
                                      </Badge>
                                    )}
                                    {ex.basedOnLesson && (
                                      <Text fontSize="xs" color="slate.500">
                                        Lesson: {ex.basedOnLesson}
                                      </Text>
                                    )}
                                  </HStack>
                                </Box>
                              </HStack>
                              <AccordionIcon />
                            </AccordionButton>

                            <AccordionPanel px={5} py={5}>
                              <VStack align="stretch" spacing={5}>
                                {/* Top Action Bar: Download Notebook Button */}
                                <HStack justify="space-between" align="center" bg="green.200" p={3} borderRadius="lg" border="1px solid" borderColor="green.600">
                                  <HStack spacing={2}>
                                    <Icon as={FiCode} color="teal.700" boxSize={5} />
                                    <Box>
                                      <Text fontSize="xs" fontWeight="bold" color="green.600">
                                        Practical Exercise Resource
                                      </Text>
                                      <Text fontSize="10px" color="green.700">
                                        {ex.format === "notebook" ? "Runnable Jupyter Notebook (.ipynb)" : "Interactive Coding Challenge"}
                                      </Text>
                                    </Box>
                                  </HStack>

                                  <Button
                                    size="sm"
                                    colorScheme="teal"
                                    leftIcon={<Icon as={FiDownload} />}
                                    onClick={() => handleDownloadNotebook(ex.notebookDownload, ex)}
                                    boxShadow="xs"
                                    _hover={{ transform: "translateY(-1px)" }}
                                  >
                                    Download Notebook
                                  </Button>
                                </HStack>

                                {/* Objectives */}
                                {ex.objective && (
                                  <Box p={4} bg="paper.50" borderRadius="lg" border="1px solid" borderColor="paper.300">
                                    <HStack spacing={2} mb={1.5}>
                                      <Text color="green.500" fontWeight="bold" fontSize="sm">✓</Text>
                                      <Text fontSize="xs" fontWeight="700" color="slate.600" textTransform="uppercase" letterSpacing="wide">
                                        OBJECTIVES
                                      </Text>
                                    </HStack>
                                    <Text fontSize="sm" color="ink.800" lineHeight="relaxed">
                                      {ex.objective}
                                    </Text>
                                  </Box>
                                )}

                                {/* Description and Context */}
                                {ex.instructions && (
                                  <Box p={4} bg="white" borderRadius="lg" border="1px solid" borderColor="paper.300">
                                    <Text fontSize="xs" fontWeight="700" color="slate.600" mb={1.5} textTransform="uppercase" letterSpacing="wide">
                                      DESCRIPTION & CONTEXT
                                    </Text>
                                    <Text fontSize="sm" color="ink.800" whiteSpace="pre-wrap" lineHeight="relaxed">
                                      {ex.instructions}
                                    </Text>
                                  </Box>
                                )}

                                {/* Topics / Concepts Covered */}
                                {ex.topics?.length > 0 && (
                                  <Box p={4} bg="white" borderRadius="lg" border="1px solid" borderColor="paper.300">
                                    <Text fontSize="xs" fontWeight="700" color="slate.600" mb={2} textTransform="uppercase" letterSpacing="wide">
                                      TOPICS / CONCEPTS COVERED
                                    </Text>
                                    <HStack spacing={2} wrap="wrap" >
                                      {ex.topics.map((tp, tpi) => (
                                        <Badge key={tpi} colorScheme="purple" bg="paper.300" color="ink.600" fontSize="xs" px={2.5} py={1} borderRadius="md" variant="subtle">
                                          - {tp}
                                        </Badge>
                                      ))}
                                    </HStack>
                                  </Box>
                                )}

                                {/* Expected Outcomes */}
                                {ex.outcomes && (
                                  <Box p={4} bg="green.50" borderRadius="lg" border="1px solid" borderColor="green.200">
                                    <Text fontSize="xs" fontWeight="700" color="green.800" mb={1.5} textTransform="uppercase" letterSpacing="wide">
                                      EXPECTED OUTCOMES
                                    </Text>
                                    <Text fontSize="sm" color="ink.800" lineHeight="relaxed">
                                      {typeof ex.outcomes === "string" ? ex.outcomes : JSON.stringify(ex.outcomes)}
                                    </Text>
                                  </Box>
                                )}

                                {/* Exercise Plan Organigram (Flow Diagram) */}
                                <ExerciseOrganigram codePlan={ex.codePlan} exerciseTitle={ex.title} />

                                {/* Repo Context Reference if matched repo exists */}
                                {ex.repo && (
                                  <Box p={3} bg="blue.50" borderRadius="lg" border="1px solid" borderColor="blue.200">
                                    <Text fontSize="xs" fontWeight="bold" color="blue.800" mb={1}>
                                      🔗 BASED ON REPOSITORY:
                                    </Text>
                                    <HStack justify="space-between">
                                      <Text fontSize="xs" color="blue.700" fontWeight="600">{ex.repo.name}</Text>
                                      {ex.repo.url && (
                                        <Link href={ex.repo.url} isExternal fontSize="xs" color="blue.600" fontWeight="bold">
                                          [View Source Code]
                                        </Link>
                                      )}
                                    </HStack>
                                  </Box>
                                )}

                                {/* Hints & Debug Hints */}
                                {ex.hints?.length > 0 && (
                                  <Box p={4} bg="paper.100" borderRadius="lg" border="1px solid" borderColor="paper.300">
                                    <Text fontSize="xs" fontWeight="700" color="slate.600" mb={2} textTransform="uppercase">
                                       PRACTICAL HINTS ({ex.hints.length})
                                    </Text>
                                    <VStack align="stretch" spacing={1.5}>
                                      {ex.hints.map((hint, hi) => (
                                        <Text key={hi} fontSize="xs" color="ink.700">• {hint}</Text>
                                      ))}
                                    </VStack>
                                  </Box>
                                )}

                                {ex.debugMode && ex.debugHint && (
                                  <Box p={3} bg="orange.50" borderRadius="lg" border="1px solid" borderColor="orange.300">
                                    <Text fontSize="xs" fontWeight="bold" color="orange.800" mb={1}>
                                       DEBUGGING CHALLENGE MODE
                                    </Text>
                                    <Text fontSize="xs" color="orange.700">{ex.debugHint}</Text>
                                  </Box>
                                )}

                                {/* Starter Code & Solution Code Accordion */}
                                {(ex.starterCode || ex.solutionCode) && (
                                  <Accordion allowToggle mt={2}>
                                    <AccordionItem border="1px solid" borderColor="paper.300" borderRadius="lg">
                                      <AccordionButton bg="paper.100" py={2.5}>
                                        <Box flex="1" textAlign="left" fontSize="xs" fontWeight="bold" color="slate.700">
                                           View Python Code Implementation Scaffold
                                        </Box>
                                        <AccordionIcon />
                                      </AccordionButton>
                                      <AccordionPanel pb={4} pt={3}>
                                        {ex.starterCode && (
                                          <Box mb={3}>
                                            <Text fontSize="xs" color="slate.600" fontWeight="bold" mb={1.5}>
                                              STARTER / SKELETON CODE:
                                            </Text>
                                            <Box
                                              p={3}
                                              bg="gray.900"
                                              color="green.300"
                                              borderRadius="md"
                                              fontFamily="mono"
                                              fontSize="xs"
                                              overflowX="auto"
                                              maxH="300px"
                                              whiteSpace="pre-wrap"
                                            >
                                              {ex.starterCode}
                                            </Box>
                                          </Box>
                                        )}

                                        {ex.solutionCode && (
                                          <Box>
                                            <Text fontSize="xs" color="slate.600" fontWeight="bold" mb={1.5}>
                                              SOLUTION CODE:
                                            </Text>
                                            <Box
                                              p={3}
                                              bg="gray.900"
                                              color="teal.200"
                                              borderRadius="md"
                                              fontFamily="mono"
                                              fontSize="xs"
                                              overflowX="auto"
                                              maxH="300px"
                                              whiteSpace="pre-wrap"
                                            >
                                              {ex.solutionCode}
                                            </Box>
                                          </Box>
                                        )}
                                      </AccordionPanel>
                                    </AccordionItem>
                                  </Accordion>
                                )}
                              </VStack>
                            </AccordionPanel>
                          </AccordionItem>
                        );
                      })}
                    </Accordion>
                  )}
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
                             {download.label || `Download Notebook ${idx + 1}`}
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
