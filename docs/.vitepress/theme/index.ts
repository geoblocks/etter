import DefaultTheme from 'vitepress/theme'
import { useData, useRouter } from 'vitepress'
import { onMounted, watch } from 'vue'
import { createMermaidRenderer } from 'vitepress-mermaid-renderer'
import './custom.css'

export default {
  extends: DefaultTheme,
  setup() {
    // The renderer does not follow VitePress's appearance switch by itself.
    const { isDark } = useData()
    watch(
      isDark,
      (dark) => createMermaidRenderer({ theme: dark ? 'dark' : 'default' }),
      { immediate: true },
    )

    const router = useRouter()
    // VitePress's client-side router intercepts all <a> clicks, including links
    // to /api/ (pdoc static HTML). Force a full browser navigation for those so
    // the plain HTML files are loaded directly instead of hitting the router.
    router.onBeforeRouteChange = (to: string) => {
      if (to.includes('/api/')) {
        window.location.href = to
        return false
      }
    }
  },
}

