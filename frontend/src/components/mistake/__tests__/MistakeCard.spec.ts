import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MistakeCard from '../MistakeCard.vue'

const item = {
  id: 'm_1',
  subject_id: 1,
  subject_name: '物理',
  kp_id: 2,
  knowledge_point: '动能定理',
  question_excerpt: '一物体在粗糙水平面上滑行……',
  status: 'wrong',
  color: '#DC2626',
  tags: ['周测', '易错'],
  error_type: 'calculation',
  source: 'image',
  last_reviewed_at: null,
  review_count: 3,
  correct_count: 1,
  wrong_count: 2,
  mastery: 0.33,
  created_at: '2026-08-10T10:00:00',
}

describe('MistakeCard（M1：列表行）', () => {
  it('渲染状态色点与中文状态文案（色点+文字，UI/UX 合规）', () => {
    const wrapper = mount(MistakeCard, { props: { item, selected: false } })
    // jsdom 会将内联样式归一化为 rgb() 形式
    expect(wrapper.find('.status-dot').attributes('style')).toContain('rgb(220, 38, 38)')
    expect(wrapper.find('.status-text').text()).toBe('未掌握')
  })

  it('渲染题干摘要与学科/知识点/错因标签', () => {
    const wrapper = mount(MistakeCard, { props: { item, selected: false } })
    expect(wrapper.find('.excerpt').text()).toContain('一物体')
    const chips = wrapper.findAll('.chip').map((c) => c.text())
    expect(chips).toContain('物理')
    expect(chips).toContain('动能定理')
    expect(chips).toContain('计算错误')
  })

  it('选中态有 selected class 且点击触发 select', async () => {
    const wrapper = mount(MistakeCard, { props: { item, selected: true } })
    expect(wrapper.classes()).toContain('selected')
    await wrapper.trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
  })
})
