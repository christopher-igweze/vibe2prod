'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import { apiFetch } from '@/lib/api/client'
import type { UserRole, UserProfile } from '@/lib/api/types'

export function useUserRole() {
  const { getToken, isSignedIn, isLoaded } = useAuth()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isLoaded) return
    if (!isSignedIn) {
      setLoading(false)
      return
    }
    let cancelled = false
    async function load() {
      try {
        const token = (await getToken()) ?? undefined
        const data = await apiFetch<UserProfile>('/api/user/me', { token })
        if (!cancelled) setProfile(data)
      } catch {
        if (!cancelled) {
          setProfile({
            user_id: '',
            role: 'user',
            onboarding_complete: false,
            lifetime_scans_used: 0,
            lifetime_scan_cap: 5,
            scan_credits: 0,
            balance_usd: 0,
          })
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [getToken, isSignedIn, isLoaded])

  return { role: (profile?.role ?? 'user') as UserRole, profile, loading }
}
