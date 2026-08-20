import { request } from './client'
import type { Organization, OrganizationMember, UsageSummary } from '../types'

export function listOrganizations() { return request<Organization[]>({ method: 'GET', url: '/organizations' }) }
export function listOrganizationMembers(id: number) { return request<OrganizationMember[]>({ method: 'GET', url: `/organizations/${id}/members` }) }
export function getOrganizationUsage(id: number) { return request<UsageSummary>({ method: 'GET', url: `/organizations/${id}/usage` }) }
