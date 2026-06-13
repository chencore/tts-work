/** Windows path → WSL2 path conversion. Mirrors backend/paths.py:win_to_wsl2. */

const WIN_PATH_RE = /^[A-Za-z]:[\\/]/;

export function winToWsl2(path: string): string {
  if (!WIN_PATH_RE.test(path)) {
    throw new Error(`不支持的路径格式（仅本地盘 X:\\...）：${path}`);
  }
  const drive = path[0].toLowerCase();
  const rest = path.slice(2).replace(/\\/g, "/");
  return `/mnt/${drive}${rest}`;
}
