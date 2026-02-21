const { maskToken } = require('../utils/encryption');

const GEMINI_ENDPOINT =
  'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent';

async function callAI(userQuery, systemPrompt) {
  const apiKey = process.env.AI_API_KEY;

  if (!apiKey) {
    throw new Error('Missing AI_API_KEY environment variable');
  }

  const payload = {
    contents: [{ parts: [{ text: userQuery }] }],
    systemInstruction: { parts: [{ text: systemPrompt }] }
  };

  const response = await fetch(`${GEMINI_ENDPOINT}?key=${apiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`AI provider error (${response.status}): ${text.slice(0, 300)}`);
  }

  const data = await response.json();

  console.info('AI execution success', {
    model: 'gemini-1.5-pro',
    keySuffix: maskToken(apiKey)
  });

  return data;
}

module.exports = { callAI };
