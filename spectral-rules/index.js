function requireVersioning(targetVal) {
  const results = [];
  try {
    const servers = (targetVal && targetVal.servers) || [];
    const paths = (targetVal && targetVal.paths) || {};
    const versionRegex = /\/v[0-9]+(\/|$)/i;
    const serverHasVersion = servers.some(s => typeof s.url === 'string' && versionRegex.test(s.url));
    const pathHasVersion = Object.keys(paths).some(p => versionRegex.test(p));
    if (!serverHasVersion && !pathHasVersion) {
      results.push({
        message: "No API version detected. Expect '/vN' in server URL or first path segment (e.g., '/v1').",
        path: [],
      });
    }
  } catch (e) {
    results.push({ message: "requireVersioning crashed: " + String(e), path: [] });
  }
  return results;
}
module.exports = { requireVersioning };
