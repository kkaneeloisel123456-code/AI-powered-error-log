/** 滚动加载统一封装（开发规划 5.2）：sentinel + IntersectionObserver + loading 锁。 */
import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

export function useInfiniteScroll(
  sentinelRef: Ref<HTMLElement | null>,
  options: { hasMore: () => boolean; loading: () => boolean; onLoadMore: () => void },
) {
  const observer = ref<IntersectionObserver | null>(null)

  onMounted(() => {
    observer.value = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && options.hasMore() && !options.loading()) {
          options.onLoadMore()
        }
      },
      { root: null, rootMargin: '200px' },
    )
    if (sentinelRef.value) observer.value.observe(sentinelRef.value)
  })

  onBeforeUnmount(() => observer.value?.disconnect())
}
