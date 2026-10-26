export function element<T extends HTMLElement = HTMLElement>(selector: string): T {
  const found = document.querySelector<T>(selector);
  if (!found) throw new Error(`Missing WebView element: ${selector}`);
  return found;
}

export function errorText(error: unknown): string {
  return error instanceof Error ? error.stack || error.message : String(error);
}
