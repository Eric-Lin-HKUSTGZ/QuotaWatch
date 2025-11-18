/**
 * 添加 API 密钥模态框组件
 * 提供表单用于添加新的 API 密钥，包含测试连接功能
 */
import { useState } from 'react'
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  Alert,
  AlertIcon,
  AlertDescription,
  Spinner,
  VStack,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
} from '@chakra-ui/react'
import { Controller, type ControllerRenderProps, useForm } from 'react-hook-form'
import { useAddKey, useTestKey } from '../../lib/api'

interface AddKeyModalProps {
  isOpen: boolean  // 模态框是否打开
  onClose: () => void  // 关闭回调函数
  platforms: Array<{ id: number; name: string; slug: string }>  // 平台列表
}

interface FormData {
  name: string  // 密钥名称
  platform_id: number  // 平台 ID
  api_key: string  // API 密钥
  total_grant?: number  // 总授予额度（仅 OpenAI 需要）
}

/**
 * 添加 API 密钥模态框
 * 功能：
 * 1. 表单输入：名称、平台、API 密钥
 * 2. 条件显示：如果选择 OpenAI，显示 total_grant 输入框
 * 3. 测试连接：在保存前测试 API 密钥是否有效
 * 4. 保存：将密钥保存到数据库
 */
export function AddKeyModal({ isOpen, onClose, platforms }: AddKeyModalProps) {
  // 测试结果状态
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  
  // 使用 react-hook-form 管理表单状态
  const { register, handleSubmit, formState: { errors }, watch, control } = useForm<FormData>()
  
  // React Query mutations
  const addKeyMutation = useAddKey()  // 添加密钥的 mutation
  const testKeyMutation = useTestKey()  // 测试密钥的 mutation

  // 监听选中的平台 ID
  const selectedPlatformId = watch('platform_id')
  const selectedPlatform = platforms.find((p) => p.id === selectedPlatformId)
  const isOpenAI = selectedPlatform?.slug === 'openai'  // 判断是否为 OpenAI 平台

  /**
   * 处理测试连接按钮点击
   * 调用测试 API，不保存到数据库
   */
  const handleTestConnection = async (data: FormData) => {
    setTestResult(null)  // 清除之前的测试结果
    try {
      // 调用测试 API
      const result = await testKeyMutation.mutateAsync({
        platform_id: data.platform_id,
        api_key: data.api_key,
        // 如果是 OpenAI，需要传递 total_grant
        metadata: isOpenAI && data.total_grant ? { total_grant: data.total_grant } : undefined,
      })
      // 显示成功消息
      setTestResult({
        success: true,
        message: `连接成功！余额: ${result.balance.toFixed(2)}${result.is_estimate ? ' (估算)' : ''}`,
      })
    } catch (error: any) {
      // 显示错误消息
      setTestResult({
        success: false,
        message: error.response?.data?.detail || error.message || '测试连接失败',
      })
    }
  }

  /**
   * 处理表单提交（保存密钥）
   */
  const onSubmit = async (data: FormData) => {
    try {
      // 调用创建 API
      await addKeyMutation.mutateAsync({
        name: data.name,
        api_key: data.api_key,
        platform_id: data.platform_id,
        // 如果是 OpenAI，需要传递 total_grant
        metadata: isOpenAI && data.total_grant ? { total_grant: data.total_grant } : undefined,
      })
      setTestResult(null)  // 清除测试结果
      onClose()  // 关闭模态框
    } catch (error) {
      // 错误处理由 mutation 自动处理
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <ModalHeader>添加 API 密钥</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              {/* 密钥名称输入 */}
              <FormControl isRequired isInvalid={!!errors.name}>
                <FormLabel>密钥名称</FormLabel>
                <Input
                  {...register('name', { required: '请输入密钥名称' })}
                  placeholder="例如: OpenRouter Production Key"
                />
              </FormControl>

              {/* 平台选择 */}
              <FormControl isRequired isInvalid={!!errors.platform_id}>
                <FormLabel>平台</FormLabel>
                <Select
                  {...register('platform_id', {
                    required: '请选择平台',
                    valueAsNumber: true,  // 将值转换为数字
                  })}
                  placeholder="选择平台"
                >
                  {platforms.map((platform) => (
                    <option key={platform.id} value={platform.id}>
                      {platform.name}
                    </option>
                  ))}
                </Select>
              </FormControl>

              {/* API 密钥输入（密码类型） */}
              <FormControl isRequired isInvalid={!!errors.api_key}>
                <FormLabel>API 密钥</FormLabel>
                <Input
                  type="password"
                  {...register('api_key', { required: '请输入 API 密钥' })}
                  placeholder="sk-..."
                />
              </FormControl>

              {/* OpenAI 平台专用：总授予额度输入 */}
              {isOpenAI && (
                <FormControl>
                  <FormLabel>总授予额度 (Total Grant)</FormLabel>
                  <Controller
                    name="total_grant"
                    control={control}
                    render={({ field }: { field: ControllerRenderProps<FormData, 'total_grant'> }) => (
                      <NumberInput
                        min={0}
                        precision={2}
                        value={field.value ?? ''}
                        onChange={(_valueAsString: string, valueAsNumber: number) =>
                          field.onChange(Number.isNaN(valueAsNumber) ? undefined : valueAsNumber)
                        }
                      >
                        <NumberInputField placeholder="例如: 100.00" />
                        <NumberInputStepper>
                          <NumberIncrementStepper />
                          <NumberDecrementStepper />
                        </NumberInputStepper>
                      </NumberInput>
                    )}
                  />
                </FormControl>
              )}

              {/* 测试结果提示 */}
              {testResult && (
                <Alert status={testResult.success ? 'success' : 'error'}>
                  <AlertIcon />
                  <AlertDescription>{testResult.message}</AlertDescription>
                </Alert>
              )}
            </VStack>
          </ModalBody>

          <ModalFooter>
            {/* 测试连接按钮 */}
            <Button
              type="button"
              variant="outline"
              mr={3}
              onClick={handleSubmit(handleTestConnection)}
              isLoading={testKeyMutation.isPending}
              loadingText="测试中..."
              leftIcon={testKeyMutation.isPending ? <Spinner size="sm" /> : undefined}
            >
              测试连接
            </Button>
            {/* 保存按钮 */}
            <Button
              type="submit"
              colorScheme="blue"
              isLoading={addKeyMutation.isPending}
              loadingText="保存中..."
            >
              保存
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  )
}
