import { useState } from "react";
import {
  Box,
  Text,
  VStack,
  HStack,
  Badge,
  Button,
  IconButton,
  SimpleGrid,
  Progress,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Select,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Textarea,
  FormControl,
  FormLabel,
  useToast,
  Divider,
} from "@chakra-ui/react";
import { Icon } from "@chakra-ui/react";
import {
  FiAward,
  FiBarChart2,
  FiTrendingUp,
  FiTrendingDown,
  FiCheckCircle,
  FiAlertTriangle,
  FiHelpCircle,
  FiDownload,
  FiPlay,
  FiActivity,
  FiTarget,
} from "react-icons/fi";
import { FaFlask, FaLightbulb } from "react-icons/fa";
import { evaluateExperimentBenchmark } from "../api.js";

const SECTION_CARD = {
  bg: "white",
  borderRadius: "card",
  border: "1px solid",
  borderColor: "paper.300",
  boxShadow: "soft",
};

const SECTION_CARD_SUBTLE = {
  bg: "paper.50",
  borderRadius: "control",
  border: "1px solid",
  borderColor: "paper.300",
};

function formatPercent(val) {
  if (val === null || val === undefined || isNaN(val)) return "N/A";
  const num = typeof val === "number" ? val : parseFloat(val);
  if (isNaN(num)) return String(val);
  if (num <= 1.0 && num >= -1.0) {
    return `${(num * 100).toFixed(1)}%`;
  }
  return `${num.toFixed(1)}%`;
}

function formatRawValue(val, metric) {
  if (val === null || val === undefined) return "N/A";
  const s = String(val);
  const mLower = String(metric || "").toLowerCase();
  if (mLower.includes("time") || mLower.includes("latency")) {
    return s.includes("ms") || s.includes("s") ? s : `${s} ms`;
  }
  const num = parseFloat(s);
  if (!isNaN(num) && num <= 1.0 && num >= 0 && !mLower.includes("loss")) {
    return `${(num * 100).toFixed(1)}%`;
  }
  return s;
}

export default function EvaluationDashboard({
  evaluations = [],
  experiments = [],
  papers = [],
  conversationId = null,
  drawerSize = "md",
  onEvaluationCreated,
}) {
  const [selectedEvalIndex, setSelectedEvalIndex] = useState(0);
  const [activeExperimentFilter, setActiveExperimentFilter] = useState("all");
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [selectedExpForEval, setSelectedExpForEval] = useState(null);
  const [submissionText, setSubmissionText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const toast = useToast();

  const gridColumns = drawerSize === "full" ? 3 : drawerSize === "lg" ? 2 : 1;

  // Filter evaluations based on active experiment filter
  const filteredEvaluations = evaluations.filter((ev) => {
    if (activeExperimentFilter === "all") return true;
    return ev.experiment_title === activeExperimentFilter;
  });

  const activeEval = filteredEvaluations[selectedEvalIndex] || filteredEvaluations[0] || evaluations[0];

  // Helper to prefill template submission text for an experiment
  const openEvaluateModal = (exp) => {
    setSelectedExpForEval(exp);
    const expTitle = exp?.title || "Experiment";
    const datasetName = typeof exp?.dataset === "object" ? exp.dataset.name : exp?.dataset || "Benchmark Dataset";
    const metricsList = (Array.isArray(exp?.metrics) ? exp.metrics : (exp?.metrics ? [exp.metrics] : ["Accuracy", "F1 Score"])).map((m) =>
      typeof m === "object" ? (m.name || m.metric) : String(m)
    );

    const sampleTemplate = `Experiment Report — ${expTitle}

Dataset: ${datasetName}
Evaluation setup: Held-out validation split with standard preprocessing.

Results:
- ${expTitle} (Proposed): ${metricsList[0] || "Accuracy"}: 91.2%, ${metricsList[1] || "F1 Score"}: 92.4%
- Baseline: ${metricsList[0] || "Accuracy"}: 87.5%, ${metricsList[1] || "F1 Score"}: 88.1%

Computational Timing:
- Inference latency: 42 ms per sample
- Training duration: 110 seconds per epoch`;

    setSubmissionText(sampleTemplate);
    setIsSubmitModalOpen(true);
  };

  const handleRunEvaluation = async () => {
    if (!selectedExpForEval) return;
    setIsSubmitting(true);
    try {
      const res = await evaluateExperimentBenchmark({
        conversationId,
        experiment: selectedExpForEval,
        submissionText,
        papersWithAnalysis: papers,
      });

      toast({
        title: "Benchmark Evaluation Completed",
        description: `Score: ${res.evaluation?.overall_score ?? "N/A"}/100 — results computed against literature baselines.`,
        status: "success",
        duration: 4000,
        isClosable: true,
      });

      setIsSubmitModalOpen(false);
      if (onEvaluationCreated) {
        onEvaluationCreated(res.evaluation, res.evaluations);
      }
    } catch (err) {
      toast({
        title: "Evaluation Failed",
        description: err.message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExportEvaluationMarkdown = (ev) => {
    if (!ev) return;
    const lines = [
      `# Benchmark Evaluation Report — ${ev.experiment_title || "Experiment"}`,
      `**Run ID:** ${ev.run_id || "Run #1"} | **Date:** ${ev.created_at ? new Date(ev.created_at).toLocaleString() : "N/A"}`,
      `**Overall Benchmark Score:** ${ev.overall_score || "N/A"}/100`,
      `**Success Rate:** ${ev.pass_rate || "N/A"}%`,
      `**Hypothesis Assessment:** ${(ev.hypothesis_check?.matches_expectation || "unclear").toUpperCase()} — ${ev.hypothesis_check?.explanation || ""}\n`,
      `## Benchmark Comparison Table\n`,
      `| Metric | Model | Student Result | Literature Baseline | Delta | Direction | Source Paper |`,
      `| :--- | :--- | :--- | :--- | :--- | :--- | :--- |`,
    ];

    (ev.comparison_table || []).forEach((r) => {
      lines.push(
        `| ${r.metric} | ${r.model} | ${r.student_reported || "N/A"} | ${r.literature_reported || "N/A"} | ${r.delta ? (r.delta > 0 ? `+${r.delta}` : r.delta) : "N/A"} | ${r.delta_direction || "N/A"} | ${r.source_paper || "Literature"} |`
      );
    });

    lines.push(`\n## Key Strengths`);
    (ev.strengths || []).forEach((s) => lines.push(`- ${s}`));

    lines.push(`\n## Weaknesses & Divergences`);
    (ev.weaknesses || []).forEach((w) => lines.push(`- ${w}`));

    lines.push(`\n## Areas for Improvement`);
    (ev.areas_for_improvement || []).forEach((a) => lines.push(`- ${a}`));

    if (ev.proposed_gap) {
      lines.push(`\n## Proposed Research Gap`);
      lines.push(`**Description:** ${ev.proposed_gap.gap_description}`);
      lines.push(`**Evidence:** ${ev.proposed_gap.supporting_evidence}`);
    }

    const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `benchmark_evaluation_${ev.run_id || "run1"}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // ==========================================
  // EMPTY STATE (No evaluations available yet)
  // ==========================================
  if (!evaluations || evaluations.length === 0) {
    return (
      <VStack align="stretch" spacing={5}>
        {/* Banner Card */}
        <Box p={6} {...SECTION_CARD} textAlign="center" position="relative" overflow="hidden">
          <Box
            position="absolute"
            top="-20px"
            right="-20px"
            w="120px"
            h="120px"
            borderRadius="full"
            bg="gold.50"
            zIndex={0}
            opacity={0.6}
          />
          <VStack spacing={3} position="relative" zIndex={1} maxW="600px" mx="auto">
            <Box
              w="54px"
              h="54px"
              borderRadius="full"
              bg="gold.100"
              color="gold.700"
              display="flex"
              alignItems="center"
              justifyContent="center"
              boxShadow="soft"
            >
              <Icon as={FiBarChart2} boxSize={6} />
            </Box>
            <Text fontSize="lg" fontWeight="bold" color="ink.900">
              No Evaluation Results Yet
            </Text>
            <Text fontSize="sm" color="slate.600" lineHeight="relaxed">
              This dashboard visualizes empirical benchmark performance, literature comparisons, pass/fail rates,
              and performance deltas once you evaluate experiment results.
            </Text>
          </VStack>
        </Box>

        {/* Actionable Next Steps: Ready Experiments */}
        {experiments.length > 0 ? (
          <Box p={5} {...SECTION_CARD}>
            <HStack justify="space-between" mb={3} align="center">
              <HStack spacing={2}>
                <Icon as={FaFlask} color="gold.600" boxSize={4} />
                <Text fontSize="sm" fontWeight="700" color="ink.900">
                  Experiments Ready for Evaluation ({experiments.length})
                </Text>
              </HStack>
              <Badge colorScheme="green" fontSize="xs" borderRadius="full" px={2.5}>
                Active Pipeline
              </Badge>
            </HStack>
            <Text fontSize="xs" color="slate.600" mb={4}>
              Select any of your generated experiments below to run an automated benchmark evaluation or submit student results:
            </Text>

            <SimpleGrid columns={drawerSize === "full" ? 2 : 1} spacing={3}>
              {experiments.map((exp, idx) => (
                <Box
                  key={idx}
                  p={4}
                  {...SECTION_CARD_SUBTLE}
                  _hover={{ borderColor: "gold.400", boxShadow: "soft" }}
                  transition="all 0.2s"
                >
                  <HStack justify="space-between" align="start" mb={2}>
                    <Badge bg="gold.100" color="gold.800" fontSize="10px" borderRadius="full" px={2}>
                      EXP {idx + 1}
                    </Badge>
                    {exp.difficulty && (
                      <Badge colorScheme="green" fontSize="10px">
                        {exp.difficulty.toUpperCase()}
                      </Badge>
                    )}
                  </HStack>
                  <Text fontSize="sm" fontWeight="bold" color="ink.900" mb={1.5} lineHeight="short">
                    {exp.title || "Untitled Experiment"}
                  </Text>
                  {exp.hypothesis && (
                    <Text fontSize="xs" color="slate.600" noOfLines={2} mb={2}>
                      <b>Hypothesis:</b> {exp.hypothesis}
                    </Text>
                  )}
                  {exp.dataset && (
                    <HStack spacing={1} mb={3}>
                      <Text fontSize="10px" fontWeight="bold" color="slate.500">Dataset:</Text>
                      <Badge fontSize="10px" colorScheme="teal" variant="subtle">
                        {typeof exp.dataset === "object" ? exp.dataset.name : exp.dataset}
                      </Badge>
                    </HStack>
                  )}

                  <Button
                    size="xs"
                    colorScheme="gold"
                    variant="solid"
                    leftIcon={<Icon as={FiPlay} />}
                    onClick={() => openEvaluateModal(exp)}
                    w="full"
                  >
                    Evaluate This Experiment
                  </Button>
                </Box>
              ))}
            </SimpleGrid>
          </Box>
        ) : (
          <Box p={5} {...SECTION_CARD_SUBTLE} textAlign="center">
            <Icon as={FiHelpCircle} color="slate.500" boxSize={6} mb={2} />
            <Text fontSize="sm" fontWeight="bold" color="ink.800" mb={1}>
              No Experiments Found in Active Context
            </Text>
            <Text fontSize="xs" color="slate.600" maxW="440px" mx="auto" mb={3}>
              First ask the assistant to <i>"generate experiments"</i> or <i>"design benchmark experiments"</i>. Once experiments are generated, you can benchmark student submissions against literature baselines.
            </Text>
          </Box>
        )}

        {/* Modal for Submitting & Evaluating Experiment */}
        <SubmissionModal
          isOpen={isSubmitModalOpen}
          onClose={() => setIsSubmitModalOpen(false)}
          experiment={selectedExpForEval}
          submissionText={submissionText}
          setSubmissionText={setSubmissionText}
          onSubmit={handleRunEvaluation}
          isSubmitting={isSubmitting}
        />
      </VStack>
    );
  }

  // ==========================================
  // DASHBOARD VIEW (Evaluations present)
  // ==========================================
  const comparisonTable = activeEval?.comparison_table || [];
  const hypothesisCheck = activeEval?.hypothesis_check || {};
  const proposedGap = activeEval?.proposed_gap;
  const overallScore = activeEval?.overall_score ?? 85.0;
  const passRate = activeEval?.pass_rate ?? 100.0;
  const meanDelta = activeEval?.mean_delta ?? 0.0;
  const strengths = activeEval?.strengths || [];
  const weaknesses = activeEval?.weaknesses || [];
  const areasForImprovement = activeEval?.areas_for_improvement || [];

  // Match associated experiment object if available
  const associatedExperiment =
    activeEval?.experiment ||
    experiments.find(
      (e) =>
        e.title &&
        activeEval?.experiment_title &&
        (e.title.toLowerCase().includes(activeEval.experiment_title.toLowerCase()) ||
          activeEval.experiment_title.toLowerCase().includes(e.title.toLowerCase()))
    );

  // Group unique experiment titles for filtering
  const uniqueExperimentTitles = Array.from(new Set(evaluations.map((e) => e.experiment_title).filter(Boolean)));

  // Determine score color
  const scoreBadgeColor = overallScore >= 85 ? "green" : overallScore >= 70 ? "orange" : "red";
  const hypMatch = String(hypothesisCheck.matches_expectation || "unclear").toLowerCase();
  const hypColor = hypMatch === "yes" ? "green" : hypMatch === "partial" ? "orange" : "red";

  return (
    <VStack align="stretch" spacing={5}>
      {/* 1. Header & Controls */}
      <Box p={4} {...SECTION_CARD}>
        <HStack justify="space-between" align="center" wrap="wrap" spacing={3}>
          <Box>
            <HStack spacing={2} align="center">
              {/* <Icon as={FiAward} color="gold.600" boxSize={5} /> */}
              <Text fontSize="md" fontWeight="700" color="ink.900">
                Experiment Benchmark Dashboard
              </Text>
            </HStack>
            <Text fontSize="xs" color="slate.600" mt="2px">
              Automated evaluation of empirical results against published literature baselines
            </Text>
          </Box>

          <HStack spacing={2}>
            {experiments.length > 0 && (
              <Button
                size="xs"
                colorScheme="gold"
                variant="outline"
                leftIcon={<Icon as={FiPlay} />}
                onClick={() => openEvaluateModal(associatedExperiment || experiments[0])}
              >
                New Evaluation Run
              </Button>
            )}
            <IconButton
              size="xs"
              variant="ghost"
              icon={<Icon as={FiDownload} />}
              aria-label="Export Markdown"
              onClick={() => handleExportEvaluationMarkdown(activeEval)}
              title="Download Benchmark Report (.md)"
            />
          </HStack>
        </HStack>

        {/* Runs & Experiment Selector */}
        <Divider my={3} borderColor="paper.300" />
        <HStack justify="space-between" align="center" wrap="wrap" spacing={2}>
          <HStack spacing={2} wrap="wrap">
            <Text fontSize="xs" fontWeight="bold" color="slate.600">
              Run:
            </Text>
            {filteredEvaluations.map((ev, idx) => (
              <Button
                key={ev.id || idx}
                size="xs"
                borderRadius="full"
                variant={idx === selectedEvalIndex ? "solid" : "outline"}
                colorScheme={idx === selectedEvalIndex ? "gold" : "gray"}
                onClick={() => setSelectedEvalIndex(idx)}
              >
                {ev.run_id || `Run #${idx + 1}`} ({ev.overall_score ?? "N/A"})
              </Button>
            ))}
          </HStack>

          {uniqueExperimentTitles.length > 1 && (
            <HStack spacing={2}>
              <Text fontSize="xs" color="slate.600">Filter Exp:</Text>
              <Select
                size="xs"
                maxW="180px"
                value={activeExperimentFilter}
                onChange={(e) => {
                  setActiveExperimentFilter(e.target.value);
                  setSelectedEvalIndex(0);
                }}
              >
                <option value="all">All Experiments</option>
                {uniqueExperimentTitles.map((t, ti) => (
                  <option key={ti} value={t}>
                    {t.length > 25 ? t.slice(0, 25) + "..." : t}
                  </option>
                ))}
              </Select>
            </HStack>
          )}

          {filteredEvaluations.length > 1 && (
            <Button
              size="xs"
              variant={compareMode ? "solid" : "ghost"}
              colorScheme="green"
              leftIcon={<Icon as={FiActivity} />}
              onClick={() => setCompareMode(!compareMode)}
            >
              {compareMode ? "Single View" : "Compare Runs"}
            </Button>
          )}
        </HStack>
      </Box>

      {/* 2. Associated Experiment Card */}
      <Box p={4} {...SECTION_CARD} bg="gold.50" borderColor="gold.200">
        <HStack justify="space-between" align="start" mb={2}>
          <HStack spacing={2}>
            <Badge colorScheme="gold" fontSize="10px" px={2.5} py={0.5} borderRadius="full">
              ASSOCIATED EXPERIMENT
            </Badge>
            {associatedExperiment?.difficulty && (
              <Badge colorScheme="green" fontSize="10px">
                {associatedExperiment.difficulty.toUpperCase()}
              </Badge>
            )}
          </HStack>
          <Badge colorScheme="green" fontSize="10px">
            {activeEval?.run_id || "Run #1"}
          </Badge>
        </HStack>

        <Text fontSize="sm" fontWeight="700" color="ink.900" mb={1.5}>
          {activeEval?.experiment_title || associatedExperiment?.title || "Experiment Benchmark"}
        </Text>

        {associatedExperiment?.dataset && (
          <HStack spacing={2} mb={2} wrap="wrap">
            <Text fontSize="xs" color="slate.600">
              <b>Dataset:</b>{" "}
              {typeof associatedExperiment.dataset === "object"
                ? associatedExperiment.dataset.name
                : associatedExperiment.dataset}
            </Text>
            {associatedExperiment.gap_addressed && (
              <Text fontSize="xs" color="slate.600">
                • <b>Target Gap:</b> {associatedExperiment.gap_addressed}
              </Text>
            )}
          </HStack>
        )}

        {/* Collapsible Configuration / Hypothesis Accordion */}
        <Accordion allowToggle mt={2}>
          <AccordionItem border="none">
            <AccordionButton p={1} _hover={{ bg: "transparent" }}>
              <Box flex="1" textAlign="left" fontSize="xs" fontWeight="bold" color="gold.800">
                Inspect Hypothesis, Baselines & Protocol Configuration
              </Box>
              <AccordionIcon color="gold.800" />
            </AccordionButton>
            <AccordionPanel pt={2} pb={1} px={1}>
              <VStack align="stretch" spacing={2} fontSize="xs" color="ink.800">
                {associatedExperiment?.hypothesis && (
                  <Box p={2.5} bg="white" borderRadius="control" border="1px solid" borderColor="paper.300">
                    <Text fontWeight="bold" color="green.700" mb={0.5}>Tested Hypothesis:</Text>
                    <Text>{associatedExperiment.hypothesis}</Text>
                  </Box>
                )}
                {associatedExperiment?.baselines && (
                  <Box p={2.5} bg="white" borderRadius="control" border="1px solid" borderColor="paper.300">
                    <Text fontWeight="bold" color="orange.700" mb={0.5}>Literature Baselines Compared:</Text>
                    <HStack spacing={1} wrap="wrap">
                      {(Array.isArray(associatedExperiment.baselines) ? associatedExperiment.baselines : [associatedExperiment.baselines]).map((b, bi) => (
                        <Badge key={bi} colorScheme="orange" fontSize="10px">
                          {typeof b === "object" ? b.name || b.baseline : String(b)}
                        </Badge>
                      ))}
                    </HStack>
                  </Box>
                )}
                {associatedExperiment?.protocol && (
                  <Box p={2.5} bg="white" borderRadius="control" border="1px solid" borderColor="paper.300">
                    <Text fontWeight="bold" color="slate.700" mb={0.5}>Protocol:</Text>
                    {Array.isArray(associatedExperiment.protocol) ? (
                      <VStack align="stretch" spacing={1} pl={2}>
                        {associatedExperiment.protocol.map((step, si) => (
                          <Text key={si}>
                            <b>{si + 1}.</b> {typeof step === "object" ? step.step || step.description : String(step)}
                          </Text>
                        ))}
                      </VStack>
                    ) : (
                      <Text>{JSON.stringify(associatedExperiment.protocol)}</Text>
                    )}
                  </Box>
                )}
              </VStack>
            </AccordionPanel>
          </AccordionItem>
        </Accordion>
      </Box>

      {/* 3. Hero KPI Stat Cards */}
      <SimpleGrid columns={drawerSize === "full" ? 4 : 2} spacing={3}>
        {/* Overall Benchmark Score */}
        <Box p={4} {...SECTION_CARD}>
          <HStack justify="space-between" mb={1}>
            <Text fontSize="xs" fontWeight="bold" color="slate.500" textTransform="uppercase">
              Overall Score
            </Text>
            <Icon as={FiAward} color={`${scoreBadgeColor}.500`} boxSize={4} />
          </HStack>
          <HStack align="baseline" spacing={2}>
            <Text fontSize="2xl" fontWeight="800" color="ink.900">
              {overallScore}
            </Text>
            <Text fontSize="xs" color="slate.500">/ 100</Text>
          </HStack>
          <Progress
            value={overallScore}
            size="xs"
            colorScheme={scoreBadgeColor}
            borderRadius="full"
            mt={2}
          />
          <Text fontSize="10px" color="slate.600" mt={1.5}>
            {overallScore >= 85 ? "Grade A • Strong Benchmark" : overallScore >= 70 ? "Grade B • Moderate Alignment" : "Grade C • Discrepancy Found"}
          </Text>
        </Box>

        {/* Hypothesis Match */}
        <Box p={4} {...SECTION_CARD}>
          <HStack justify="space-between" mb={1}>
            <Text fontSize="xs" fontWeight="bold" color="slate.500" textTransform="uppercase">
              Hypothesis
            </Text>
            <Icon
              as={hypMatch === "yes" ? FiCheckCircle : FiAlertTriangle}
              color={`${hypColor}.500`}
              boxSize={4}
            />
          </HStack>
          <Badge colorScheme={hypColor} fontSize="sm" px={2.5} py={0.5} borderRadius="md" mt={1}>
            {hypMatch.toUpperCase()}
          </Badge>
          <Text fontSize="xs" color="ink.700" mt={2} noOfLines={2} title={hypothesisCheck.explanation}>
            {hypothesisCheck.explanation || "No explanation provided."}
          </Text>
        </Box>

        {/* Success / Pass Rate */}
        <Box p={4} {...SECTION_CARD}>
          <HStack justify="space-between" mb={1}>
            <Text fontSize="xs" fontWeight="bold" color="slate.500" textTransform="uppercase">
              Pass / Success Rate
            </Text>
            <Icon as={FiTarget} color="teal.500" boxSize={4} />
          </HStack>
          <HStack align="baseline" spacing={1}>
            <Text fontSize="2xl" fontWeight="800" color="ink.900">
              {passRate}%
            </Text>
          </HStack>
          <Progress value={passRate} size="xs" colorScheme="teal" borderRadius="full" mt={2} />
          <Text fontSize="10px" color="slate.600" mt={1.5}>
            % of metrics meeting or beating literature
          </Text>
        </Box>

        {/* Mean Delta vs SOTA */}
        <Box p={4} {...SECTION_CARD}>
          <HStack justify="space-between" mb={1}>
            <Text fontSize="xs" fontWeight="bold" color="slate.500" textTransform="uppercase">
              Mean Delta vs SOTA
            </Text>
            <Icon
              as={meanDelta >= 0 ? FiTrendingUp : FiTrendingDown}
              color={meanDelta >= 0 ? "green.500" : "red.500"}
              boxSize={4}
            />
          </HStack>
          <HStack align="baseline" spacing={1}>
            <Text
              fontSize="2xl"
              fontWeight="800"
              color={meanDelta >= 0 ? "green.700" : "red.600"}
            >
              {meanDelta > 0 ? `+${(meanDelta * 100).toFixed(1)}%` : `${(meanDelta * 100).toFixed(1)}%`}
            </Text>
          </HStack>
          <Text fontSize="10px" color="slate.600" mt={3}>
            {comparisonTable.length} metric(s) evaluated across models
          </Text>
        </Box>
      </SimpleGrid>

      {/* Multi-Run Progression & Comparison (if compareMode or multiple runs) */}
      {compareMode && filteredEvaluations.length > 1 && (
        <MultiRunComparisonView evaluations={filteredEvaluations} />
      )}

      {/* 4. Visual Benchmark Charts */}
      {comparisonTable.length > 0 && (
        <Box p={4} {...SECTION_CARD}>
          <HStack justify="space-between" mb={3}>
            <HStack spacing={2}>
              <Icon as={FiBarChart2} color="gold.700" boxSize={4} />
              <Text fontSize="xs" fontWeight="700" color="ink.900" textTransform="uppercase" letterSpacing="wide">
                Visual Benchmark Comparison
              </Text>
            </HStack>
            <HStack spacing={3} fontSize="10px">
              <HStack spacing={1}>
                <Box w="10px" h="10px" bg="gold.500" borderRadius="xs" />
                <Text color="slate.600">Student Result</Text>
              </HStack>
              <HStack spacing={1}>
                <Box w="10px" h="10px" bg="green.600" borderRadius="xs" />
                <Text color="slate.600">Literature Baseline</Text>
              </HStack>
            </HStack>
          </HStack>

          <VStack align="stretch" spacing={4} pt={2}>
            {comparisonTable.map((row, rIdx) => {
              const sNorm = row.student_normalized !== null ? row.student_normalized : (typeof row.student_reported === "number" ? row.student_reported : null);
              const lNorm = row.literature_normalized !== null ? row.literature_normalized : (typeof row.literature_reported === "number" ? row.literature_reported : null);
              const metricName = (row.metric || "Metric").replace(/_/g, " ").toUpperCase();

              // Calculate width percentages for display
              const sPercent = sNorm !== null ? (sNorm <= 1.0 ? sNorm * 100 : Math.min(100, (sNorm / 100) * 100)) : 70;
              const lPercent = lNorm !== null ? (lNorm <= 1.0 ? lNorm * 100 : Math.min(100, (lNorm / 100) * 100)) : 0;
              const delta = row.delta;
              const dir = row.delta_direction;

              return (
                <Box key={rIdx} p={3} {...SECTION_CARD_SUBTLE}>
                  <HStack justify="space-between" mb={2} align="center">
                    <HStack spacing={2}>
                      <Text fontSize="xs" fontWeight="bold" color="ink.900">
                        {metricName}
                      </Text>
                      {row.model && (
                        <Badge fontSize="10px" colorScheme="gray" variant="subtle">
                          {row.model}
                        </Badge>
                      )}
                    </HStack>
                    <HStack spacing={2}>
                      {dir === "higher" && (
                        <Badge colorScheme="green" fontSize="10px" px={2}>
                          Outperformed ({delta ? `+${(delta * 100).toFixed(1)}%` : "higher"})
                        </Badge>
                      )}
                      {dir === "match" && (
                        <Badge colorScheme="green" fontSize="10px" px={2}>
                          Baseline Match
                        </Badge>
                      )}
                      {dir === "lower" && (
                        <Badge colorScheme="red" fontSize="10px" px={2}>
                          Lagging ({delta ? `${(delta * 100).toFixed(1)}%` : "lower"})
                        </Badge>
                      )}
                      {dir === "no_literature_match" && (
                        <Badge colorScheme="green" fontSize="10px" px={2}>
                          Novel Metric
                        </Badge>
                      )}
                    </HStack>
                  </HStack>

                  {/* Dual comparative progress bars */}
                  <VStack align="stretch" spacing={1.5}>
                    {/* Student Bar */}
                    <Box>
                      <HStack justify="space-between" fontSize="10px" mb="2px">
                        <Text color="gold.800" fontWeight="600">Student Submission</Text>
                        <Text fontWeight="bold" color="ink.900">{formatRawValue(row.student_reported, row.metric)}</Text>
                      </HStack>
                      <Box w="100%" bg="paper.200" h="10px" borderRadius="full" overflow="hidden">
                        <Box w={`${Math.min(100, Math.max(5, sPercent))}%`} bg="gold.500" h="100%" borderRadius="full" transition="width 0.4s" />
                      </Box>
                    </Box>

                    {/* Literature Bar (if available) */}
                    {row.literature_reported !== null && row.literature_reported !== undefined && (
                      <Box>
                        <HStack justify="space-between" fontSize="10px" mb="2px">
                          <Text color="green.700" fontWeight="600">Literature Target ({row.source_paper || "Paper"})</Text>
                          <Text fontWeight="bold" color="ink.900">{formatRawValue(row.literature_reported, row.metric)}</Text>
                        </HStack>
                        <Box w="100%" bg="paper.200" h="10px" borderRadius="full" overflow="hidden">
                          <Box w={`${Math.min(100, Math.max(5, lPercent))}%`} bg="green.600" h="100%" borderRadius="full" transition="width 0.4s" />
                        </Box>
                      </Box>
                    )}
                  </VStack>
                </Box>
              );
            })}
          </VStack>
        </Box>
      )}

      {/* 5. Benchmark Comparison Table */}
      {comparisonTable.length > 0 && (
        <Box p={4} {...SECTION_CARD}>
          <Text fontSize="xs" fontWeight="700" color="ink.900" mb={3} textTransform="uppercase" letterSpacing="wide">
            Benchmark Comparison Table
          </Text>
          <Box overflowX="auto">
            <Table size="sm" variant="simple">
              <Thead bg="paper.100">
                <Tr>
                  <Th color="slate.600">Metric</Th>
                  <Th color="slate.600">Model</Th>
                  <Th color="slate.600" isNumeric>Student</Th>
                  <Th color="slate.600" isNumeric>Literature</Th>
                  <Th color="slate.600" isNumeric>Delta (Δ)</Th>
                  <Th color="slate.600">Status</Th>
                  <Th color="slate.600">Citation</Th>
                </Tr>
              </Thead>
              <Tbody>
                {comparisonTable.map((r, ri) => {
                  const d = r.delta;
                  const dir = r.delta_direction;
                  return (
                    <Tr key={ri} _hover={{ bg: "paper.50" }}>
                      <Td fontWeight="600" color="ink.900">
                        {r.metric}
                      </Td>
                      <Td color="ink.700">{r.model}</Td>
                      <Td isNumeric fontWeight="700" color="gold.800">
                        {formatRawValue(r.student_reported, r.metric)}
                      </Td>
                      <Td isNumeric color="slate.700">
                        {formatRawValue(r.literature_reported, r.metric)}
                      </Td>
                      <Td isNumeric fontWeight="bold">
                        {d !== null && d !== undefined ? (
                          <Text as="span" color={d > 0.005 ? "green.600" : d < -0.005 ? "red.600" : "green.600"}>
                            {d > 0 ? `+${(d * 100).toFixed(1)}%` : `${(d * 100).toFixed(1)}%`}
                          </Text>
                        ) : (
                          <Text as="span" color="slate.400">—</Text>
                        )}
                      </Td>
                      <Td>
                        <Badge
                          fontSize="10px"
                          colorScheme={
                            dir === "higher"
                              ? "green"
                              : dir === "match"
                              ? "green"
                              : dir === "lower"
                              ? "red"
                              : "green"
                          }
                        >
                          {dir === "higher"
                            ? "Outperformed"
                            : dir === "match"
                            ? "Matched"
                            : dir === "lower"
                            ? "Lagged"
                            : "New Metric"}
                        </Badge>
                      </Td>
                      <Td fontSize="10px" color="slate.500" maxW="150px" isTruncated title={r.source_paper}>
                        {r.source_paper || "N/A"}
                      </Td>
                    </Tr>
                  );
                })}
              </Tbody>
            </Table>
          </Box>
        </Box>
      )}

      {/* 6. Strengths, Weaknesses & Improvement Areas */}
      <SimpleGrid columns={drawerSize === "full" ? 3 : 1} spacing={4}>
        {/* Strengths */}
        <Box p={4} {...SECTION_CARD} borderLeftWidth="4px" borderLeftColor="green.500">
          <HStack spacing={2} mb={2}>
            <Icon as={FiCheckCircle} color="green.600" boxSize={4} />
            <Text fontSize="xs" fontWeight="700" color="green.800" textTransform="uppercase" letterSpacing="wide">
              Key Strengths ({strengths.length})
            </Text>
          </HStack>
          <VStack align="stretch" spacing={2} fontSize="xs" color="ink.800">
            {strengths.map((st, si) => (
              <HStack key={si} align="start" spacing={2}>
                <Text color="green.600" fontWeight="bold">•</Text>
                <Text lineHeight="short">{st}</Text>
              </HStack>
            ))}
          </VStack>
        </Box>

        {/* Weaknesses */}
        <Box p={4} {...SECTION_CARD} borderLeftWidth="4px" borderLeftColor="red.400">
          <HStack spacing={2} mb={2}>
            <Icon as={FiAlertTriangle} color="red.500" boxSize={4} />
            <Text fontSize="xs" fontWeight="700" color="red.800" textTransform="uppercase" letterSpacing="wide">
              Weaknesses & Divergences ({weaknesses.length})
            </Text>
          </HStack>
          <VStack align="stretch" spacing={2} fontSize="xs" color="ink.800">
            {weaknesses.map((wk, wi) => (
              <HStack key={wi} align="start" spacing={2}>
                <Text color="red.500" fontWeight="bold">•</Text>
                <Text lineHeight="short">{wk}</Text>
              </HStack>
            ))}
          </VStack>
        </Box>

        {/* Areas for Improvement */}
        <Box p={4} {...SECTION_CARD} borderLeftWidth="4px" borderLeftColor="gold.500">
          <HStack spacing={2} mb={2}>
            <Icon as={FaLightbulb} color="gold.600" boxSize={4} />
            <Text fontSize="xs" fontWeight="700" color="gold.800" textTransform="uppercase" letterSpacing="wide">
              Areas for Improvement ({areasForImprovement.length})
            </Text>
          </HStack>
          <VStack align="stretch" spacing={2} fontSize="xs" color="ink.800">
            {areasForImprovement.map((imp, ii) => (
              <HStack key={ii} align="start" spacing={2}>
                <Text color="gold.600" fontWeight="bold">•</Text>
                <Text lineHeight="short">{imp}</Text>
              </HStack>
            ))}
          </VStack>
        </Box>
      </SimpleGrid>

      {/* 7. Candidate Research Gap Discovered Alert */}
      {proposedGap && (
        <Box p={4} {...SECTION_CARD} bg="orange.50" borderColor="orange.300">
          <HStack spacing={2} mb={2} align="center">
            <Icon as={FiAlertTriangle} color="orange.700" boxSize={4} />
            <Text fontSize="xs" fontWeight="bold" color="orange.900" textTransform="uppercase">
              New Candidate Research Gap Discovered from Empirical Discrepancy
            </Text>
          </HStack>
          <Text fontSize="sm" fontWeight="700" color="ink.900" mb={1}>
            {proposedGap.gap_description}
          </Text>
          {proposedGap.supporting_evidence && (
            <Text fontSize="xs" color="ink.700" mb={1.5}>
              <b>Evidence:</b> {proposedGap.supporting_evidence}
            </Text>
          )}
          {proposedGap.opportunity && (
            <Text fontSize="xs" color="orange.800">
              <b>Research Opportunity:</b> {proposedGap.opportunity}
            </Text>
          )}
        </Box>
      )}

      {/* Submission Modal */}
      <SubmissionModal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        experiment={selectedExpForEval}
        submissionText={submissionText}
        setSubmissionText={setSubmissionText}
        onSubmit={handleRunEvaluation}
        isSubmitting={isSubmitting}
      />
    </VStack>
  );
}

// ==========================================
// SUBMISSION / EVALUATION MODAL
// ==========================================
function SubmissionModal({
  isOpen,
  onClose,
  experiment,
  submissionText,
  setSubmissionText,
  onSubmit,
  isSubmitting,
}) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent bg="paper.50">
        <ModalHeader borderBottom="1px solid" borderColor="paper.300" fontSize="sm">
          <HStack spacing={2}>
            <Icon as={FiBarChart2} color="gold.600" />
            <Text>Run Benchmark Evaluation</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody py={4}>
          <VStack align="stretch" spacing={3}>
            {experiment && (
              <Box p={3} {...SECTION_CARD_SUBTLE}>
                <Text fontSize="xs" fontWeight="bold" color="gold.800" mb={1}>
                  Target Experiment:
                </Text>
                <Text fontSize="sm" fontWeight="600" color="ink.900">
                  {experiment.title}
                </Text>
              </Box>
            )}

            <FormControl>
              <FormLabel fontSize="xs" fontWeight="bold" color="slate.700">
                Student Experiment Results (Plain text, log, or summary):
              </FormLabel>
              <Textarea
                rows={9}
                fontSize="xs"
                fontFamily="mono"
                value={submissionText}
                onChange={(e) => setSubmissionText(e.target.value)}
                placeholder="Paste your notebook outputs, metric printouts, or summary..."
                bg="white"
                borderColor="paper.300"
              />
            </FormControl>

            <Text fontSize="10px" color="slate.500">
              The evaluation engine extracts numbers literally present in your submission, normalizes metrics (Accuracy, F1, Latency, etc.), and compares them mathematically with published literature baselines.
            </Text>
          </VStack>
        </ModalBody>
        <ModalFooter borderTop="1px solid" borderColor="paper.300">
          <Button size="sm" variant="ghost" mr={2} onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="sm"
            colorScheme="gold"
            isLoading={isSubmitting}
            loadingText="Evaluating Benchmark..."
            onClick={onSubmit}
          >
            Compute Evaluation
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

// ==========================================
// MULTI-RUN COMPARISON VIEW
// ==========================================
function MultiRunComparisonView({ evaluations = [] }) {
  if (!evaluations || evaluations.length < 2) return null;

  return (
    <Box p={4} {...SECTION_CARD} bg="green.50" borderColor="green.200">
      <HStack justify="space-between" align="center" mb={3}>
        <HStack spacing={2}>
          <Icon as={FiTrendingUp} color="green.700" boxSize={4} />
          <Text fontSize="xs" fontWeight="700" color="green.900" textTransform="uppercase" letterSpacing="wide">
            Performance Progression Across {evaluations.length} Runs
          </Text>
        </HStack>
        <Badge colorScheme="green" fontSize="10px">
          Multi-Run Trend
        </Badge>
      </HStack>

      <SimpleGrid columns={evaluations.length} spacing={3}>
        {evaluations.map((ev, i) => {
          const prev = i > 0 ? evaluations[i - 1] : null;
          const scoreDiff = prev ? (ev.overall_score || 0) - (prev.overall_score || 0) : null;

          return (
            <Box key={i} p={3} bg="white" borderRadius="control" border="1px solid" borderColor="green.200">
              <HStack justify="space-between" mb={1}>
                <Badge bg="green.100" color="green.800" fontSize="10px">
                  {ev.run_id || `Run #${i + 1}`}
                </Badge>
                {scoreDiff !== null && (
                  <Badge colorScheme={scoreDiff >= 0 ? "green" : "red"} fontSize="9px">
                    {scoreDiff >= 0 ? `+${scoreDiff.toFixed(1)}` : scoreDiff.toFixed(1)} pts
                  </Badge>
                )}
              </HStack>
              <Text fontSize="lg" fontWeight="800" color="ink.900">
                {ev.overall_score ?? "N/A"}<Text as="span" fontSize="xs" color="slate.500">/100</Text>
              </Text>
              <Text fontSize="10px" color="slate.600" mt={1}>
                Success: {ev.pass_rate ?? "N/A"}%
              </Text>
              <Text fontSize="9px" color="green.700" fontWeight="600" mt={1} isTruncated title={ev.experiment_title}>
                {ev.experiment_title}
              </Text>
            </Box>
          );
        })}
      </SimpleGrid>
    </Box>
  );
}
