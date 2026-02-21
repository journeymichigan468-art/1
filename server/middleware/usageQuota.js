const usageByUser = new Map();

const ROLE_LIMITS = {
  free: 5,
  pro: 100,
  admin: Number.POSITIVE_INFINITY
};

function enforceQuota(req, res, next) {
  const userId = req.user?.sub || req.user?.id;
  if (!userId) {
    return res.status(400).json({ error: 'Token must include sub or id claim' });
  }

  const role = req.user?.role || 'free';
  const maxExecutions = ROLE_LIMITS[role] ?? ROLE_LIMITS.free;

  const record = usageByUser.get(userId) || { count: 0 };

  if (record.count >= maxExecutions) {
    return res.status(429).json({
      error: 'Quota exceeded',
      role,
      maxExecutions
    });
  }

  record.count += 1;
  usageByUser.set(userId, record);
  req.usage = { current: record.count, maxExecutions, role };

  return next();
}

module.exports = { enforceQuota };
