export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export async function post(path: string): Promise<void> {
  const res = await fetch(path, { method: "POST" });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
}
