import { useEffect } from "react"

export function useChatScroll(ref, dep) {
  useEffect(() => {
    if (ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
  }, [dep])
}
