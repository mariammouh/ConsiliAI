import { useState } from "react";
import {
  Box,
  Container,
  Flex,
  Heading,
  Text,
  Button,
  VStack,
  HStack,
  SimpleGrid,
  Image,
  Badge,
  Icon,
  Link as ChakraLink,
  useColorModeValue,
} from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";
import {
  FiBookOpen,
  FiLayers,
  FiArrowRight,
  FiCheckCircle,
  FiDownload,
  FiLogIn,
  FiUserPlus,
  FiCpu,
} from "react-icons/fi";
import { FaFlask, FaLaptopCode, FaLightbulb } from "react-icons/fa";
import { isLoggedIn, logout } from "../api.js";

export default function Home() {
  const [authenticated, setAuthenticated] = useState(() => isLoggedIn());

  const bgPage = useColorModeValue("paper.200", "gray.900");
  const bgCard = useColorModeValue("white", "gray.800");
  const bgCardSubtle = useColorModeValue("paper.100", "gray.700");
  const borderColor = useColorModeValue("paper.300", "gray.700");
  const textPrimary = useColorModeValue("ink.900", "gray.100");
  const textSecondary = useColorModeValue("ink.600", "gray.300");
  const textMuted = useColorModeValue("slate.500", "gray.400");
  const navBg = useColorModeValue("rgba(245, 239, 201, 0.92)", "rgba(26, 32, 44, 0.92)");

  const handleLogout = () => {
    logout();
    setAuthenticated(false);
  };

  const capabilities = [
    {
      icon: FiBookOpen,
      tag: "LITERATURE & GAPS",
      title: "Automated Literature Synthesis",
      desc: "Searches peer-reviewed papers, extracts core methodologies, and isolates unexplored research gaps to establish an evidence-based foundation.",
    },
    {
      icon: FiCpu,
      tag: "TECHNICAL BLUEPRINTS",
      title: "Structured Research Architecture",
      desc: "Transforms high-level research concepts into concrete technical plans, detailing model architectures, datasets, and execution milestones.",
    },
    {
      icon: FiLayers,
      tag: "CURRICULUM CREATION",
      title: "Pedagogical Course Design",
      desc: "Converts advanced academic breakthroughs into accessible, multi-week university syllabi with lecture outlines and structured learning objectives.",
    },
    {
      icon: FaLaptopCode,
      tag: "PRACTICAL LABS",
      title: "Hands-on Lab Formulation",
      desc: "Generates reproducible student coding assignments, step-by-step lab manuals, and assessment rubrics for immediate classroom deployment.",
    },
    {
      icon: FaFlask,
      tag: "VERIFICATION & BENCHMARKS",
      title: "Experiment Design & Metrics",
      desc: "Outlines baseline comparisons, control groups, and empirical evaluation frameworks to validate concepts rigorously.",
    },
    {
      icon: FiDownload,
      tag: "DIRECT EXPORT",
      title: "Lecture Slide & ZIP Packages",
      desc: "Export ready-to-teach PowerPoint presentations (.pptx), structured documentation, and full project archives with a single click.",
    },
  ];

  const workflowSteps = [
    {
      step: "01",
      title: "Define Research or Upload Papers",
      desc: "Input a research question, emerging thesis, or upload academic PDFs. ConsiliAI parses your domain and pinpoints existing state of the art.",
    },
    {
      step: "02",
      title: "Multi-Agent Synthesis",
      desc: "Autonomous specialized agents orchestrate literature cross-referencing, technical feasibility checks, and pedagogical translations in tandem.",
    },
    {
      step: "03",
      title: "Deploy Courseware & Labs",
      desc: "Review your organized research ledger, inspect synthesized modules, and export presentation decks and lab exercises directly for your students.",
    },
  ];

  return (
    <Box minH="100vh" bg={bgPage} color={textPrimary} display="flex" flexDirection="column">
      {/* Navigation Header */}
      <Box
        as="header"
        position="sticky"
        top={0}
        zIndex={50}
        bg={navBg}
        backdropFilter="blur(8px)"
        borderBottom="1px solid"
        borderColor={borderColor}
        py={3}
        px={{ base: 4, md: 8 }}
      >
        <Container maxW="7xl">
          <Flex align="center" justify="space-between">
            {/* Logo and brand name */}
            <HStack as={RouterLink} to="/" spacing={3} _hover={{ textDecoration: "none" }}>
              <Image
                src="/logo.png"
                alt="ConsiliAI Logo"
                h={{ base: "42px", md: "50px" }}
                objectFit="contain"
                fallback={
                  <Text fontFamily="mono" fontSize="sm" fontWeight="bold" color="gold.600">
                    [ CONSILIAI ]
                  </Text>
                }
              />
              <Box display={{ base: "none", sm: "block" }}>
                <Text fontSize="lg" fontWeight="700" lineHeight="1.1" color="ink.900">
                  ConsiliAI
                </Text>
                <Text
                  fontFamily="mono"
                  fontSize="2xs"
                  color="slate.500"
                  letterSpacing="wider"
                  textTransform="uppercase"
                >
                  Research-to-Education
                </Text>
              </Box>
            </HStack>

            {/* Navigation links & CTA */}
            <HStack spacing={{ base: 2, md: 4 }}>
              <ChakraLink
                as="a"
                href="#features"
                fontSize="sm"
                fontWeight="500"
                color={textSecondary}
                display={{ base: "none", md: "inline-flex" }}
                _hover={{ color: "gold.600", textDecoration: "none" }}
                px={3}
                py={1}
              >
                Capabilities
              </ChakraLink>
              <ChakraLink
                as="a"
                href="#workflow"
                fontSize="sm"
                fontWeight="500"
                color={textSecondary}
                display={{ base: "none", md: "inline-flex" }}
                _hover={{ color: "gold.600", textDecoration: "none" }}
                px={3}
                py={1}
              >
                How It Works
              </ChakraLink>

              {authenticated ? (
                <HStack spacing={2}>
                  <Button
                    as={RouterLink}
                    to="/chat"
                    variant="solid"
                    size="sm"
                    rightIcon={<FiArrowRight />}
                    px={4}
                  >
                    Open Workspace
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleLogout}
                    color={textMuted}
                    _hover={{ bg: bgCardSubtle, color: textPrimary }}
                  >
                    Sign out
                  </Button>
                </HStack>
              ) : (
                <HStack spacing={2}>
                  <Button
                    as={RouterLink}
                    to="/login"
                    variant="ghost"
                    size="sm"
                    leftIcon={<FiLogIn />}
                    color={textSecondary}
                    _hover={{ bg: bgCardSubtle, color: textPrimary }}
                  >
                    Sign in
                  </Button>
                  <Button
                    as={RouterLink}
                    to="/register"
                    variant="solid"
                    size="sm"
                    leftIcon={<FiUserPlus />}
                    px={4}
                  >
                    Get Started
                  </Button>
                </HStack>
              )}
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* Hero Section */}
      <Box as="section" pt={{ base: 12, md: 20 }} pb={{ base: 12, md: 16 }} px={4}>
        <Container maxW="5xl" textAlign="center">
          <Badge
            display="inline-flex"
            alignItems="center"
            gap={1.5}
            fontFamily="mono"
            fontSize="xs"
            px={3}
            py={1}
            borderRadius="pill"
            bg="gold.50"
            color="gold.600"
            border="1px solid"
            borderColor="paper.400"
            mb={6}
          >
            <Icon as={FaLightbulb} boxSize={3} />
            RESEARCH-TO-EDUCATION TRANSFER PLATFORM
          </Badge>

          <Heading
            as="h1"
            fontSize={{ base: "2.2rem", sm: "3rem", md: "3.75rem" }}
            fontWeight="800"
            lineHeight="1.15"
            letterSpacing="-0.02em"
            color="ink.900"
            mb={6}
          >
            Bridge the gap between{" "}
            <Text as="span" color="gold.500">
              cutting-edge research
            </Text>{" "}
            and university pedagogy.
          </Heading>

          <Text
            fontSize={{ base: "md", md: "xl" }}
            color={textSecondary}
            maxW="3xl"
            mx="auto"
            mb={10}
            lineHeight="1.6"
          >
            ConsiliAI translates dense scientific literature into structured course syllabi,
            actionable technical roadmaps, hands-on student lab exercises, and exportable slide presentations.
          </Text>

          {/* Primary Call to Action */}
          <Flex
            direction={{ base: "column", sm: "row" }}
            justify="center"
            align="center"
            gap={4}
            mb={12}
          >
            {authenticated ? (
              <Button
                as={RouterLink}
                to="/chat"
                size="lg"
                variant="solid"
                rightIcon={<FiArrowRight />}
                px={8}
                h="54px"
                fontSize="md"
                boxShadow="card"
              >
                Go to Research Workspace
              </Button>
            ) : (
              <>
                <Button
                  as={RouterLink}
                  to="/register"
                  size="lg"
                  variant="solid"
                  rightIcon={<FiArrowRight />}
                  px={8}
                  h="54px"
                  fontSize="md"
                  boxShadow="card"
                >
                  Start Transfer Project
                </Button>
                <Button
                  as={RouterLink}
                  to="/login"
                  size="lg"
                  variant="outline"
                  borderColor="paper.400"
                  color="ink.800"
                  bg="white"
                  _hover={{ bg: "paper.100", borderColor: "gold.500" }}
                  px={8}
                  h="54px"
                  fontSize="md"
                >
                  Sign in to Account
                </Button>
              </>
            )}
          </Flex>

          {/* Key Value Highlights */}
          <HStack
            spacing={{ base: 4, md: 8 }}
            justify="center"
            wrap="wrap"
            fontSize="sm"
            color={textMuted}
          >
            <HStack spacing={1.5}>
              <Icon as={FiCheckCircle} color="gold.500" />
              <Text fontWeight="500">Academic Gap Analysis</Text>
            </HStack>
            <HStack spacing={1.5}>
              <Icon as={FiCheckCircle} color="gold.500" />
              <Text fontWeight="500">Curriculum & Syllabus Generation</Text>
            </HStack>
            <HStack spacing={1.5}>
              <Icon as={FiCheckCircle} color="gold.500" />
              <Text fontWeight="500">Classroom Lab Protocols</Text>
            </HStack>
            <HStack spacing={1.5}>
              <Icon as={FiCheckCircle} color="gold.500" />
              <Text fontWeight="500">PowerPoint (.pptx) Slide Export</Text>
            </HStack>
          </HStack>
        </Container>
      </Box>

      {/* Interactive Transfer Ledger Preview Card */}
      <Box as="section" pb={{ base: 12, md: 20 }} px={4}>
        <Container maxW="5xl">
          <Box
            bg={bgCard}
            borderRadius="card"
            border="1px solid"
            borderColor={borderColor}
            boxShadow="card"
            p={{ base: 5, md: 8 }}
          >
            <Flex
              direction={{ base: "column", sm: "row" }}
              justify="space-between"
              align={{ base: "flex-start", sm: "center" }}
              borderBottom="1px solid"
              borderColor={borderColor}
              pb={4}
              mb={6}
              gap={2}
            >
              <HStack spacing={3}>
                <Image src="/logo.png" alt="ConsiliAI" h="36px" objectFit="contain" />
                <Box>
                  <Text fontSize="sm" fontWeight="700" color={textPrimary}>
                    ConsiliAI Project State Ledger
                  </Text>
                  <Text fontFamily="mono" fontSize="2xs" color={textMuted}>
                    Autonomous Research-to-Pedagogy Synthesis
                  </Text>
                </Box>
              </HStack>
              <Badge
                bg="gold.50"
                color="gold.600"
                border="1px solid"
                borderColor="paper.400"
                fontFamily="mono"
                fontSize="xs"
                px={2.5}
                py={0.5}
                borderRadius="md"
              >
                LIVE AGENT PIPELINE
              </Badge>
            </Flex>

            {/* 4 Representative Ledger Items */}
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
              <Box
                bg={bgCardSubtle}
                p={4}
                borderRadius="control"
                border="1px solid"
                borderColor={borderColor}
              >
                <HStack spacing={2} mb={2}>
                  <Icon as={FiBookOpen} color="gold.500" />
                  <Text fontSize="xs" fontFamily="mono" color="slate.500" fontWeight="600">
                    LITERATURE & GAPS
                  </Text>
                </HStack>
                <Text fontSize="sm" fontWeight="600" color={textPrimary} mb={1}>
                  Grounding & Citation Synthesis
                </Text>
                <Text fontSize="xs" color={textSecondary} lineHeight="1.5">
                  Synthesizes relevant arXiv and journal publications, identifying empirical
                  limitations and formulation opportunities.
                </Text>
              </Box>

              <Box
                bg={bgCardSubtle}
                p={4}
                borderRadius="control"
                border="1px solid"
                borderColor={borderColor}
              >
                <HStack spacing={2} mb={2}>
                  <Icon as={FiCpu} color="gold.500" />
                  <Text fontSize="xs" fontFamily="mono" color="slate.500" fontWeight="600">
                    TECHNICAL ARCHITECTURE
                  </Text>
                </HStack>
                <Text fontSize="sm" fontWeight="600" color={textPrimary} mb={1}>
                  Rigorous Methodology Planning
                </Text>
                <Text fontSize="xs" color={textSecondary} lineHeight="1.5">
                  Drafts technical system requirements, formal mathematical definitions, and model
                  training or evaluation specifications.
                </Text>
              </Box>

              <Box
                bg={bgCardSubtle}
                p={4}
                borderRadius="control"
                border="1px solid"
                borderColor={borderColor}
              >
                <HStack spacing={2} mb={2}>
                  <Icon as={FiLayers} color="gold.500" />
                  <Text fontSize="xs" fontFamily="mono" color="slate.500" fontWeight="600">
                    TEACHING & COURSE
                  </Text>
                </HStack>
                <Text fontSize="sm" fontWeight="600" color={textPrimary} mb={1}>
                  Multi-Week Syllabus & Slide Outlines
                </Text>
                <Text fontSize="xs" color={textSecondary} lineHeight="1.5">
                  Translates research depth into graduate or undergraduate modules with weekly learning
                  goals and exportable presentation slides.
                </Text>
              </Box>

              <Box
                bg={bgCardSubtle}
                p={4}
                borderRadius="control"
                border="1px solid"
                borderColor={borderColor}
              >
                <HStack spacing={2} mb={2}>
                  <Icon as={FaLaptopCode} color="gold.500" />
                  <Text fontSize="xs" fontFamily="mono" color="slate.500" fontWeight="600">
                    STUDENT LABS & EXPERIMENTS
                  </Text>
                </HStack>
                <Text fontSize="sm" fontWeight="600" color={textPrimary} mb={1}>
                  Reproducible Lab Exercises
                </Text>
                <Text fontSize="xs" color={textSecondary} lineHeight="1.5">
                  Prepares turnkey code assignments, data verification pipelines, and empirical
                  benchmarks for university laboratory sessions.
                </Text>
              </Box>
            </SimpleGrid>
          </Box>
        </Container>
      </Box>

      {/* Core Capabilities Section */}
      <Box as="section" id="features" py={{ base: 12, md: 16 }} bg={bgCardSubtle} px={4}>
        <Container maxW="6xl">
          <Box textAlign="center" mb={{ base: 10, md: 14 }}>
            <Text
              fontFamily="mono"
              fontSize="xs"
              color="slate.500"
              letterSpacing="wider"
              textTransform="uppercase"
              mb={2}
            >
              [ CAPABILITIES ]
            </Text>
            <Heading fontSize={{ base: "2xl", md: "3xl" }} color="ink.900" mb={3}>
              Designed for Researchers, Educators, and Academic Labs
            </Heading>
            <Text fontSize="md" color={textSecondary} maxW="2xl" mx="auto">
              Every feature is built around the authentic workflow of turning complex scientific
              discoveries into structured, high-impact education.
            </Text>
          </Box>

          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
            {capabilities.map((c, i) => {
              const CapIcon = c.icon;
              return (
                <Box
                  key={i}
                  bg={bgCard}
                  p={6}
                  borderRadius="card"
                  border="1px solid"
                  borderColor={borderColor}
                  boxShadow="soft"
                  transition="all 0.2s"
                  _hover={{ borderColor: "gold.400", boxShadow: "cardHover" }}
                >
                  <Flex
                    w={10}
                    h={10}
                    align="center"
                    justify="center"
                    borderRadius="control"
                    bg="gold.50"
                    color="gold.600"
                    mb={4}
                  >
                    <Icon as={CapIcon} boxSize={5} />
                  </Flex>
                  <Text
                    fontFamily="mono"
                    fontSize="2xs"
                    color="slate.500"
                    letterSpacing="wider"
                    mb={1}
                  >
                    {c.tag}
                  </Text>
                  <Heading fontSize="md" fontWeight="700" color="ink.900" mb={2}>
                    {c.title}
                  </Heading>
                  <Text fontSize="sm" color={textSecondary} lineHeight="1.6">
                    {c.desc}
                  </Text>
                </Box>
              );
            })}
          </SimpleGrid>
        </Container>
      </Box>

      {/* How It Works Section */}
      <Box as="section" id="workflow" py={{ base: 12, md: 20 }} px={4}>
        <Container maxW="5xl">
          <Box textAlign="center" mb={{ base: 10, md: 14 }}>
            <Text
              fontFamily="mono"
              fontSize="xs"
              color="slate.500"
              letterSpacing="wider"
              textTransform="uppercase"
              mb={2}
            >
              [ WORKFLOW ]
            </Text>
            <Heading fontSize={{ base: "2xl", md: "3xl" }} color="ink.900" mb={3}>
              From Research Paper to the Lecture Hall in Three Steps
            </Heading>
            <Text fontSize="md" color={textSecondary} maxW="xl" mx="auto">
              A transparent, inspectable orchestration process that maintains complete academic rigor.
            </Text>
          </Box>

          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={8}>
            {workflowSteps.map((s, idx) => (
              <Box
                key={idx}
                bg={bgCard}
                p={6}
                borderRadius="card"
                border="1px solid"
                borderColor={borderColor}
                boxShadow="soft"
                position="relative"
              >
                <Text
                  fontFamily="mono"
                  fontSize="2xl"
                  fontWeight="800"
                  color="gold.500"
                  mb={3}
                >
                  {s.step}
                </Text>
                <Heading fontSize="md" fontWeight="700" color="ink.900" mb={2}>
                  {s.title}
                </Heading>
                <Text fontSize="sm" color={textSecondary} lineHeight="1.6">
                  {s.desc}
                </Text>
              </Box>
            ))}
          </SimpleGrid>
        </Container>
      </Box>

      
      

      {/* Footer */}
      <Box
        as="footer"
        mt="auto"
        bg={bgCardSubtle}
        borderTop="1px solid"
        borderColor={borderColor}
        py={6}
        px={4}
      >
        <Container maxW="7xl">
          <Flex
            direction={{ base: "column", sm: "row" }}
            justify="space-between"
            align="center"
            gap={4}
          >
            <HStack spacing={2} align="center">
              <Image src="/logo.png" alt="ConsiliAI Logo" h="28px" objectFit="contain" />
              <Text fontSize="xs" color={textMuted}>
                ConsiliAI &copy; {new Date().getFullYear()} &middot; Research-to-Education Transfer
              </Text>
            </HStack>

            <HStack spacing={4} fontSize="xs" color={textSecondary}>
              <ChakraLink as={RouterLink} to="/login" _hover={{ color: "gold.600" }}>
                Sign in
              </ChakraLink>
              <Text color={textMuted}>&bull;</Text>
              <ChakraLink as={RouterLink} to="/register" _hover={{ color: "gold.600" }}>
                Create account
              </ChakraLink>
              <Text color={textMuted}>&bull;</Text>
              <ChakraLink as={RouterLink} to="/chat" _hover={{ color: "gold.600" }}>
                Workspace
              </ChakraLink>
            </HStack>
          </Flex>
        </Container>
      </Box>
    </Box>
  );
}
