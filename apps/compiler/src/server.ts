/**
 * Fastify HTTP server for TSX compilation service.
 * Provides POST /compile endpoint for the backend to use.
 */

import Fastify from 'fastify';
import { z } from 'zod';
import { compileTsx, isCompilerAvailable } from './compile.js';

const CompileRequestSchema = z.object({
  sourceCode: z.string().min(1),
  componentName: z.string().min(1),
  siteId: z.string().min(1),
});

const fastify = Fastify({
  logger: {
    level: process.env.LOG_LEVEL || 'info',
  },
});

// Health check
fastify.get('/health', async () => {
  return {
    status: 'ok',
    compiler: isCompilerAvailable() ? 'available' : 'unavailable',
    timestamp: new Date().toISOString(),
  };
});

// Compilation endpoint
fastify.post('/compile', async (request, reply) => {
  try {
    const parsed = CompileRequestSchema.safeParse(request.body);

    if (!parsed.success) {
      return reply.code(400).send({
        success: false,
        error: 'Invalid request body',
        details: parsed.error.errors,
      });
    }

    const result = await compileTsx(parsed.data);

    if (!result.success) {
      return reply.code(422).send(result);
    }

    return reply.send(result);
  } catch (err: any) {
    fastify.log.error({ err }, 'Compilation request failed');
    return reply.code(500).send({
      success: false,
      error: err?.message || 'Internal server error',
    });
  }
});

// Start server
const start = async () => {
  try {
    const port = parseInt(process.env.PORT || '3001', 10);
    const host = process.env.HOST || '0.0.0.0';

    await fastify.listen({ port, host });
    fastify.log.info(`Compiler service listening on ${host}:${port}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
