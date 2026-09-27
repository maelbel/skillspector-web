export function formatDate(seconds: number) {
  return new Date(seconds * 1000).toLocaleString()
}
