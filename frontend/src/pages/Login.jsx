import { useState } from "react";
import {
  Box,
  Heading,
  Text,
  Input,
  Button,
  VStack,
  FormControl,
  FormLabel,
  Alert,
  AlertIcon,
  Link as ChakraLink,
} from "@chakra-ui/react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { login } from "../api.js";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/chat");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box minH="100vh" bg="paper.100" display="flex" alignItems="center" justifyContent="center" px={4}>
      <Box
        as="form"
        onSubmit={handleSubmit}
        bg="paper.50"
        border="1px solid"
        borderColor="paper.300"
        borderRadius="lg"
        p={10}
        w="full"
        maxW="420px"
      >
        <Text fontFamily="mono" fontSize="xs" color="slate.500" letterSpacing="wide" mb={2}>
          [ CONSILIAI ]
        </Text>
        <Heading fontSize="2xl" mb={1} color="ink.900">
          Sign in
        </Heading>
        <Text fontSize="sm" color="ink.500" mb={6}>
          Research-to-education transfer assistant
        </Text>

        {error && (
          <Alert status="error" borderRadius="md" mb={4} fontSize="sm">
            <AlertIcon />
            {error}
          </Alert>
        )}

        <VStack spacing={4} align="stretch">
          <FormControl isRequired>
            <FormLabel fontSize="sm">Email</FormLabel>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@university.edu"
              autoComplete="email"
            />
          </FormControl>
          <FormControl isRequired>
            <FormLabel fontSize="sm">Password</FormLabel>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </FormControl>
          <Button type="submit" isLoading={loading} mt={2}>
            Sign in
          </Button>
        </VStack>

        <Text fontSize="sm" color="ink.500" mt={6} textAlign="center">
          No account yet?{" "}
          <ChakraLink as={RouterLink} to="/register" color="slate.500" fontWeight="600">
            Create one
          </ChakraLink>
        </Text>
      </Box>
    </Box>
  );
}
