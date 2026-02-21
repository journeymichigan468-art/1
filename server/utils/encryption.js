const crypto = require('crypto');

function hashPrompt(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function maskToken(secret) {
  if (!secret || secret.length < 6) return '***';
  return `***${secret.slice(-4)}`;
}

module.exports = { hashPrompt, maskToken };
