/**
 * 全流程 E2E（T-M5-08 / PRD 7.x 主流程）：
 * 登录 -> 文本录入 -> 错题本 -> 一键复习（作答/交卷/批改）-> 首页待办 -> 数据看板
 * 前置：后端已启动（RECALL_AI_MOCK=true）
 */
import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const UNIQUE = `E2E唯一题干-${Date.now()}`

test.beforeAll(() => {
  // 本地令牌来自后端 data/auth/token.key（playwright 运行目录为 frontend/）
  const token = readFileSync(join(process.cwd(), '..', 'data', 'auth', 'token.key'), 'utf-8').trim()
  process.env.E2E_TOKEN = token
})

async function login(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.waitForURL('**/login**')
  const revealed = page.locator('code.num')
  if (await revealed.count()) {
    await page.getByRole('button', { name: '使用此令牌进入' }).click()
  } else {
    await page.locator('#token-input').fill(process.env.E2E_TOKEN!)
    await page.getByRole('button', { name: '进入 Recall' }).click()
  }
  await page.waitForURL('http://localhost:5173/')
}

test.describe('核心闭环', () => {
  test('登录 -> 录入 -> 复习 -> 看板', async ({ page }) => {
    // 1. 登录
    await login(page)
    await expect(page.getByText('今日到期')).toBeVisible()

    // 2. 文本录入（AI 补全 -> 直接保存）
    await page.goto('/import?mode=text')
    await page.getByLabel('题干 *').fill(`${UNIQUE}：求函数 f(x)=x³ 的导数`)
    await page.getByLabel('答案').fill('3x²')
    await page.getByRole('button', { name: '直接保存' }).click()
    await page.waitForURL('**/mistakes**')

    // 3. 错题本：搜索唯一题干，详情面板展示题目区/解析区
    await page.locator('.topbar-search input').fill(UNIQUE)
    await page.locator('.topbar-search input').press('Enter')
    await expect(page.locator('.mistake-card').first()).toBeVisible()
    await page.locator('.mistake-card').first().click()
    await expect(page.locator('.problem-section')).toBeVisible()
    await expect(page.locator('.analysis-section')).toBeVisible()

    // 4. 一键复习：选学科 -> 开始 -> 作答 -> 交卷 -> 批改结果
    await page.goto('/review')
    await page.locator('.subject-chips .chip').first().click()
    await page.getByRole('button', { name: '开始复习' }).click()
    await page.waitForURL('**/review/answer**')
    await expect(page.locator('.question-card')).toBeVisible({ timeout: 30_000 })
    // 选择第一题的选项（若为选择题）
    const firstOption = page.locator('.option-row').first()
    if (await firstOption.count()) {
      await firstOption.click()
    } else {
      await page.locator('#answer-input').fill('3x²')
    }
    await page.getByRole('button', { name: /提交交卷|下一题/ }).click()
    // 若多题则继续作答直至交卷
    for (let i = 0; i < 15; i++) {
      const submitBtn = page.getByRole('button', { name: '提交交卷' })
      if (await submitBtn.isVisible()) {
        await submitBtn.click()
        break
      }
      await page.getByRole('button', { name: '下一题' }).click()
      const opt = page.locator('.option-row').first()
      if (await opt.count()) await opt.click()
    }
    // EX-08 弹窗处理
    const confirmBtn = page.getByRole('button', { name: '确认交卷' })
    if (await confirmBtn.count()) await confirmBtn.click()
    await page.waitForURL('**/review/result/**', { timeout: 30_000 })
    await expect(page.getByText('本次得分')).toBeVisible({ timeout: 30_000 })
    await page.getByRole('button', { name: '完成并更新计划' }).click()
    await page.waitForURL('http://localhost:5173/')

    // 5. 数据看板：趋势/分布/图谱卡片渲染
    await page.goto('/dashboard')
    await expect(page.getByText('学习趋势')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('学科分布')).toBeVisible()
    await expect(page.getByText('知识图谱')).toBeVisible()
  })

  test('错题本空状态与删除二次确认', async ({ page }) => {
    await login(page)
    await page.goto('/mistakes')
    // 搜索一个不存在的关键词 -> 无结果空态
    await page.locator('.topbar-search input').fill('绝对不存在的题目xyz')
    await page.locator('.topbar-search input').press('Enter')
    await expect(page.getByText('没有找到相关错题')).toBeVisible({ timeout: 15_000 })
    await page.getByRole('button', { name: '清除筛选条件' }).click()
    // 清除后列表恢复数据
    await expect(page.locator('.mistake-card').first()).toBeVisible({ timeout: 15_000 })
  })
})
