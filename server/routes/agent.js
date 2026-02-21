const express = require('express');
const { callAI } = require('../services/aiService');
const { verifyToken, signToken } = require('../middleware/auth');
const { limiter } = require('../middleware/rateLimiter');
const { enforceQuota } = require('../middleware/usageQuota');
const { hashPrompt } = require('../utils/encryption');

const router = express.Router();

router.post('/auth/token', (req, res) => {
  const { userId, role = 'free' } = req.body || {};
  if (!userId) {
    return res.status(400).json({ error: 'userId is required' });
  }

  const token = signToken({ sub: userId, role }, process.env.JWT_SECRET);
  return res.json({ token, role });
});

router.post('/execute', verifyToken, limiter, enforceQuota, async (req, res) => {
  const { subtask, systemPrompt } = req.body;

  if (!subtask || !systemPrompt) {
    return res
      .status(400)
      .json({ error: 'Both subtask and systemPrompt are required' });
  }

  try {
    const result = await callAI(subtask, systemPrompt);

    console.info('Execution logged', {
      userId: req.user.sub,
      role: req.user.role,
      promptHash: hashPrompt(subtask),
      usage: req.usage
    });

    return res.json({ result, usage: req.usage });
  } catch (error) {
    console.error('Execution failed', {
      userId: req.user?.sub,
      message: error.message
    });

    return res.status(502).json({ error: 'AI execution failed' });
  }
});

module.exports = router;
