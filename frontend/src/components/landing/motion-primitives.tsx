"use client"

import { useRef, useEffect, type ReactNode } from "react"
import {
  motion,
  useInView,
  useMotionValue,
  useSpring,
  useTransform,
} from "motion/react"

/* ── Fade + slide in when scrolled into view ── */
export function FadeInWhenVisible({
  children,
  delay = 0,
  y = 40,
  className = "",
}: {
  children: ReactNode
  delay?: number
  y?: number
  className?: string
}) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-80px" })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y }}
      transition={{ duration: 0.6, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

/* ── 3D perspective card that tracks mouse ── */
export function TiltCard({
  children,
  className = "",
}: {
  children: ReactNode
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [8, -8]), {
    stiffness: 300,
    damping: 30,
  })
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-8, 8]), {
    stiffness: 300,
    damping: 30,
  })

  function handleMouseMove(e: React.MouseEvent) {
    const rect = ref.current?.getBoundingClientRect()
    if (!rect) return
    x.set((e.clientX - rect.left) / rect.width - 0.5)
    y.set((e.clientY - rect.top) / rect.height - 0.5)
  }

  function handleMouseLeave() {
    x.set(0)
    y.set(0)
  }

  return (
    <motion.div
      ref={ref}
      style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={className}
    >
      {children}
    </motion.div>
  )
}

/* ── Animated number counter that springs from 0 ── */
export function AnimatedCounter({
  target,
  suffix = "",
  prefix = "",
}: {
  target: number
  suffix?: string
  prefix?: string
}) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true })
  const springValue = useSpring(0, { stiffness: 80, damping: 20 })
  const display = useTransform(springValue, (v) => `${prefix}${Math.round(v)}${suffix}`)

  useEffect(() => {
    if (isInView) springValue.set(target)
  }, [isInView, target, springValue])

  return <motion.span ref={ref}>{display}</motion.span>
}
