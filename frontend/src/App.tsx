/**
 * 主应用组件
 * 这是应用的根组件，包含主要的 UI 结构
 * 注意：这是一个基础版本，实际应用中应该包含路由、认证检查等功能
 */
import { Box, Container, Heading } from '@chakra-ui/react'

function App() {
  return (
    <Container maxW="container.xl" py={8}>
      <Box>
        <Heading size="lg" mb={4}>
          QuotaWatch
        </Heading>
        <p>API Key Quota Monitoring Dashboard</p>
        {/* TODO: 在这里添加实际的 UI 组件，如：
            - 密钥列表
            - 添加密钥按钮
            - 余额显示
            - 余额历史图表等
        */}
      </Box>
    </Container>
  )
}

export default App
