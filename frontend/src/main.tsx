/**
 * 应用入口文件
 * 负责初始化 React 应用、配置全局提供者（Chakra UI、React Query）
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import { ChakraProvider } from '@chakra-ui/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'

// 创建 React Query 客户端实例
// 配置默认选项，如缓存策略、重试策略等
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,  // 窗口获得焦点时不自动重新获取数据
      retry: 1,  // 失败时重试 1 次
    },
  },
})

// 渲染应用根组件
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/* React Query 提供者：为应用提供数据获取和缓存功能 */}
    <QueryClientProvider client={queryClient}>
      {/* Chakra UI 提供者：为应用提供 UI 组件和主题 */}
      <ChakraProvider>
        <App />
      </ChakraProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
