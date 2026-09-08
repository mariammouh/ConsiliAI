import { useState } from "react";
import {
  Box,
  Heading,
  Text,
  Input,
  Button,
  VStack,
  HStack,
  FormControl,
  FormLabel,
  FormHelperText,
  Alert,
  AlertIcon,
  Link as ChakraLink,
  Image,
  InputGroup,
  InputRightElement,
  IconButton,
  useColorModeValue,
} from "@chakra-ui/react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { FiArrowLeft, FiEye, FiEyeOff } from "react-icons/fi";
import { register, login } from "../api.js";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const bgMain = useColorModeValue("paper.200", "gray.900");
  const bgCard = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("paper.300", "gray.700");
  const textPrimary = useColorModeValue("ink.900", "gray.100");
  const textSecondary = useColorModeValue("ink.600", "gray.300");
  const textMuted = useColorModeValue("slate.500", "gray.400");
  const inputBg = useColorModeValue("paper.100", "gray.700");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match. Please re-enter.");
      return;
    }

    setLoading(true);
    try {
      await register(email, password);
      // Automatically log the user in after registration
      await login(email, password);
      navigate("/chat");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box
      minH="100vh"
      bg={bgMain}
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      p={{ base: 4, sm: 6 }}
    >
      <Box w="full" maxW="440px">
        {/* Return to Home link */}
        <HStack mb={4} justify="flex-start">
          <ChakraLink
            as={RouterLink}
            to="/"
            display="inline-flex"
            alignItems="center"
            gap={1.5}
            fontSize="xs"
            fontFamily="mono"
            color={textMuted}
            _hover={{ color: "gold.600", textDecoration: "none" }}
          >
            <FiArrowLeft />
            <span>RETURN TO HOME</span>
          </ChakraLink>
        </HStack>

        {/* Main Card */}
        <Box
          as="form"
          onSubmit={handleSubmit}
          bg={bgCard}
          border="1px solid"
          borderColor={borderColor}
          borderRadius="card"
          boxShadow="card"
          p={{ base: 6, sm: 8 }}
        >
          {/* Brand Header */}
          <VStack spacing={2} align="center" textAlign="center" mb={6}>
            <ChakraLink as={RouterLink} to="/" _hover={{ opacity: 0.9 }}>
              <Image
                src="/logo.png"
                alt="ConsiliAI"
                h="64px"
                objectFit="contain"
                fallback={
                  <Text fontFamily="mono" fontSize="xs" color="gold.600" letterSpacing="wide">
                    [ CONSILIAI ]
                  </Text>
                }
              />
            </ChakraLink>
            <Box>
              <Heading fontSize="xl" fontWeight="700" color={textPrimary} mb={1}>
                Create an account
              </Heading>
              <Text fontSize="xs" color={textSecondary}>
                Research-to-Education Transfer Platform
              </Text>
            </Box>
          </VStack>

          {error && (
            <Alert
              status="error"
              borderRadius="control"
              mb={5}
              fontSize="xs"
              bg="red.50"
              color="red.800"
              border="1px solid"
              borderColor="red.200"
            >
              <AlertIcon boxSize={3.5} color="red.500" />
              {error}
            </Alert>
          )}

          <VStack spacing={4} align="stretch">
            <FormControl isRequired>
              <FormLabel fontSize="xs" fontWeight="600" color={textPrimary} mb={1}>
                Academic / Organization Email
              </FormLabel>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="researcher@institution.org"
                autoComplete="email"
                bg={inputBg}
                borderColor={borderColor}
                borderRadius="control"
                fontSize="sm"
                h="42px"
                focusBorderColor="gold.500"
                _hover={{ borderColor: "paper.400" }}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="xs" fontWeight="600" color={textPrimary} mb={1}>
                Password
              </FormLabel>
              <InputGroup size="md">
                <Input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  autoComplete="new-password"
                  bg={inputBg}
                  borderColor={borderColor}
                  borderRadius="control"
                  fontSize="sm"
                  h="42px"
                  focusBorderColor="gold.500"
                  _hover={{ borderColor: "paper.400" }}
                  pr="2.5rem"
                />
                <InputRightElement h="42px" width="2.5rem">
                  <IconButton
                    h="1.75rem"
                    size="xs"
                    variant="ghost"
                    onClick={() => setShowPassword(!showPassword)}
                    icon={showPassword ? <FiEyeOff /> : <FiEye />}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    color={textMuted}
                    _hover={{ bg: "transparent", color: textPrimary }}
                  />
                </InputRightElement>
              </InputGroup>
              <FormHelperText fontSize="2xs" color={textMuted} mt={1}>
                Must be at least 8 characters long.
              </FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="xs" fontWeight="600" color={textPrimary} mb={1}>
                Confirm Password
              </FormLabel>
              <InputGroup size="md">
                <Input
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat your password"
                  autoComplete="new-password"
                  bg={inputBg}
                  borderColor={borderColor}
                  borderRadius="control"
                  fontSize="sm"
                  h="42px"
                  focusBorderColor="gold.500"
                  _hover={{ borderColor: "paper.400" }}
                  pr="2.5rem"
                />
                <InputRightElement h="42px" width="2.5rem">
                  <IconButton
                    h="1.75rem"
                    size="xs"
                    variant="ghost"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    icon={showConfirmPassword ? <FiEyeOff /> : <FiEye />}
                    aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                    color={textMuted}
                    _hover={{ bg: "transparent", color: textPrimary }}
                  />
                </InputRightElement>
              </InputGroup>
            </FormControl>

            <Button
              type="submit"
              variant="solid"
              isLoading={loading}
              mt={3}
              h="44px"
              fontSize="sm"
              fontWeight="600"
              borderRadius="control"
              boxShadow="0px 4px 10px rgba(188, 108, 37, 0.25)"
            >
              Create Account
            </Button>
          </VStack>

          <Box mt={6} pt={5} borderTop="1px solid" borderColor={borderColor} textAlign="center">
            <Text fontSize="xs" color={textSecondary}>
              Already have an account?{" "}
              <ChakraLink
                as={RouterLink}
                to="/login"
                color="gold.600"
                fontWeight="600"
                _hover={{ color: "gold.700", textDecoration: "underline" }}
              >
                Sign in
              </ChakraLink>
            </Text>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
