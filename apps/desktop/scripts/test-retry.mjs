#!/usr/bin/env node

/**
 * 测试 fetchWithRetry 函数的重试机制
 * 模拟 GitHub API 的 403 速率限制和网络错误
 */

import { createServer } from 'http'

// ==================== 测试服务器 ====================

let requestCount = 0

const server = createServer((req, res) => {
  requestCount++
  const currentCount = requestCount
  
  console.log(`[Server] Request #${currentCount} received`)
  
  // 模拟 403 速率限制响应
  if (currentCount <= 2) {
    console.log(`[Server] Returning 403 Rate Limit response`)
    res.writeHead(403, {
      'Content-Type': 'application/json',
      'X-RateLimit-Reset': Math.floor(Date.now() / 1000) + 2, // 2秒后重置
      'Retry-After': '2'
    })
    res.end(JSON.stringify({ message: 'API rate limit exceeded' }))
    return
  }
  
  // 第三次请求返回成功
  console.log(`[Server] Returning 200 OK response`)
  res.writeHead(200, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify({
    tag_name: 'v2026.06.09',
    name: 'yt-dlp 2026.06.09'
  }))
})

const PORT = 18932

await new Promise((resolve) => {
  server.listen(PORT, () => {
    console.log(`[Test] Mock server listening on port ${PORT}\n`)
    resolve()
  })
})

// ==================== 测试函数 ====================

/**
 * 复制原脚本中的 fetchWithRetry 逻辑用于测试
 */
const fetchWithRetry = async (url, options, maxRetries = 3) => {
  let lastResponse = null
  let lastError = null

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, options)
      lastResponse = response

      // 403 通常表示速率限制，尝试重试
      if (response.status === 403 && attempt < maxRetries) {
        const retryAfter = response.headers.get('X-RateLimit-Reset')
        if (retryAfter) {
          const waitTime = (parseInt(retryAfter, 10) * 1000 - Date.now()) + 1000
          if (waitTime > 0 && waitTime < 120000) {
            console.error(`[retry] Rate limit hit. Waiting ${Math.ceil(waitTime / 1000)}s before retry ${attempt}/${maxRetries}...`)
            await new Promise((resolve) => setTimeout(resolve, waitTime))
            continue
          }
        }
        // 如果没有 X-RateLimit-Reset 头，等待固定时间
        console.error(`[retry] Rate limit (403). Waiting 30s before retry ${attempt}/${maxRetries}...`)
        await new Promise((resolve) => setTimeout(resolve, 30000))
        continue
      }

      // 成功响应或非 403 错误，立即返回
      if (response.ok || attempt === maxRetries) {
        return response
      }

      // 其他客户端错误（4xx），不重试
      if (response.status >= 400 && response.status < 500) {
        return response
      }

      // 服务器错误（5xx），尝试重试
      if (attempt < maxRetries) {
        console.error(`[retry] Server error ${response.status}. Retrying ${attempt}/${maxRetries}...`)
        await new Promise((resolve) => setTimeout(resolve, 5000 * attempt))
        continue
      }
    } catch (error) {
      lastError = error
      if (attempt < maxRetries) {
        console.error(`[retry] Request failed: ${error.message}. Retrying ${attempt}/${maxRetries}...`)
        await new Promise((resolve) => setTimeout(resolve, 5000 * attempt))
      }
    }
  }

  // 所有重试都用完，抛出最后一次错误（如果有）或返回最后一次响应
  if (lastError) {
    throw lastError
  }
  if (lastResponse) {
    return lastResponse
  }
  throw new Error(`Request to ${url} failed after ${maxRetries} retries with no response`)
}

// ==================== 测试用例 ====================

const results = []

// 测试 1: 403 速率限制后成功
console.log('=' .repeat(60))
console.log('TEST 1: 403 Rate Limit → Success after retries')
console.log('=' .repeat(60))

try {
  const startTime = Date.now()
  const response = await fetchWithRetry(`http://localhost:${PORT}/api/releases/latest`, {})
  const elapsed = Date.now() - startTime
  
  if (response.ok) {
    const data = await response.json()
    console.log(`[PASS] Success after ${elapsed}ms`)
    console.log(`[PASS] Response: ${JSON.stringify(data)}`)
    results.push({ name: '403 → Success', passed: true, elapsed })
  } else {
    console.log(`[FAIL] Unexpected status: ${response.status}`)
    results.push({ name: '403 → Success', passed: false, error: `Status ${response.status}` })
  }
} catch (error) {
  console.log(`[FAIL] ${error.message}`)
  results.push({ name: '403 → Success', passed: false, error: error.message })
}

console.log()

// 测试 2: 网络错误后成功
console.log('=' .repeat(60))
console.log('TEST 2: Network Error → Success after retries')
console.log('=' .repeat(60))

// 创建一个会先抛出网络错误的测试
let netErrorCount = 0
const mockFetchWithError = async (url, options) => {
  netErrorCount++
  if (netErrorCount <= 2) {
    throw new Error(`ECONNREFUSED: Connection refused (attempt ${netErrorCount})`)
  }
  return { ok: true, status: 200, json: async () => ({ tag_name: 'v2026.06.09' }) }
}

// 替换 fetchWithRetry 中的 fetch 进行测试
const originalFetch = global.fetch
global.fetch = mockFetchWithError

try {
  const startTime = Date.now()
  const response = await fetchWithRetry('http://example.com/api', {}, 3)
  const elapsed = Date.now() - startTime
  
  console.log(`[PASS] Recovered after ${elapsed}ms, ${netErrorCount} attempts`)
  results.push({ name: 'Network Error → Success', passed: true, elapsed })
} catch (error) {
  console.log(`[FAIL] ${error.message}`)
  results.push({ name: 'Network Error → Success', passed: false, error: error.message })
}

global.fetch = originalFetch
console.log()

// 测试 3: 超过最大重试次数（返回最后一次响应）
console.log('=' .repeat(60))
console.log('TEST 3: Exceed max retries (returns last response)')
console.log('=' .repeat(60))

let always403Count = 0
const mockFetchAlways403 = async () => {
  always403Count++
  return { ok: false, status: 403, statusText: 'Forbidden', headers: new Map([['X-RateLimit-Reset', '0']]) }
}

global.fetch = mockFetchAlways403

try {
  const response = await fetchWithRetry('http://example.com/api', {}, 3)
  if (always403Count === 3 && response.status === 403) {
    console.log(`[PASS] Returned last response after ${always403Count} attempts (status: ${response.status})`)
    results.push({ name: 'Max Retries Exceeded', passed: true, attempts: always403Count })
  } else {
    console.log(`[FAIL] Expected 3 attempts with 403, got ${always403Count} attempts with status ${response?.status}`)
    results.push({ name: 'Max Retries Exceeded', passed: false, error: `Expected 3 attempts, got ${always403Count}` })
  }
} catch (error) {
  console.log(`[FAIL] Should return response, not throw: ${error.message}`)
  results.push({ name: 'Max Retries Exceeded', passed: false, error: error.message })
}

global.fetch = originalFetch
console.log()

// 测试 4: 无 X-RateLimit-Reset 头的 403（等待 30s 固定时间后重试）
console.log('=' .repeat(60))
console.log('TEST 4: 403 without X-RateLimit-Reset header (uses 30s fallback)')
console.log('=' .repeat(60))

let noHeaderCount = 0
const mockFetchNoHeader = async () => {
  noHeaderCount++
  return { 
    ok: false, 
    status: 403, 
    statusText: 'Forbidden', 
    headers: new Map(), // 空 headers
    text: async () => 'Rate limited'
  }
}

global.fetch = mockFetchNoHeader

try {
  const startTime = Date.now()
  const response = await fetchWithRetry('http://example.com/api', {}, 2)
  const elapsed = Date.now() - startTime
  // 应该返回最后一次响应，并且等待了约 60 秒（两次 30 秒）
  if (noHeaderCount === 2 && response.status === 403) {
    console.log(`[PASS] Returned last response after ${noHeaderCount} attempts (${elapsed}ms)`)
    results.push({ name: '403 No Header', passed: true, attempts: noHeaderCount, elapsed })
  } else {
    console.log(`[FAIL] Expected 2 attempts, got ${noHeaderCount}`)
    results.push({ name: '403 No Header', passed: false, error: `Expected 2 attempts, got ${noHeaderCount}` })
  }
} catch (error) {
  console.log(`[FAIL] Should return response, not throw: ${error.message}`)
  results.push({ name: '403 No Header', passed: false, error: error.message })
}

global.fetch = originalFetch
console.log()

// ==================== 停止服务器 ====================

server.close()

// ==================== 测试结果汇总 ====================

console.log('=' .repeat(60))
console.log('TEST SUMMARY')
console.log('=' .repeat(60))

let passed = 0
let failed = 0

for (const result of results) {
  const status = result.passed ? '✓ PASS' : '✗ FAIL'
  console.log(`  ${status}: ${result.name}`)
  if (result.elapsed) console.log(`         Time: ${result.elapsed}ms`)
  if (result.error) console.log(`         Error: ${result.error}`)
  if (result.attempts) console.log(`         Attempts: ${result.attempts}`)
  
  if (result.passed) passed++
  else failed++
}

console.log()
console.log(`Total: ${results.length} | Passed: ${passed} | Failed: ${failed}`)

if (failed > 0) {
  process.exit(1)
}