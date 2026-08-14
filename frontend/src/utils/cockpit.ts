/** 复习专注舱（UI/UX 2.4 / 方案 C）：深色舱位切换，保留滚动与输入内容。 */
export function enableCockpit() {
  document.documentElement.classList.add('cockpit')
}

export function disableCockpit() {
  document.documentElement.classList.remove('cockpit')
}

export function isCockpitEnabled(): boolean {
  return document.documentElement.classList.contains('cockpit')
}
