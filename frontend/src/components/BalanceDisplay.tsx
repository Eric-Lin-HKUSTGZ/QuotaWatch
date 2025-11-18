/**
 * 余额显示组件
 * 用于显示 API 密钥的余额，如果是估算值则显示特殊标记和提示
 */
import { Text, Tooltip } from '@chakra-ui/react'

interface BalanceDisplayProps {
  balance: number  // 余额值
  isEstimate: boolean  // 是否为估算值
}

/**
 * 余额显示组件
 * - 如果是精确值：直接显示余额
 * - 如果是估算值：显示 ~ 前缀，并在鼠标悬停时显示提示信息
 */
export function BalanceDisplay({ balance, isEstimate }: BalanceDisplayProps) {
  // 如果是估算值，在余额前添加 ~ 符号
  const displayBalance = isEstimate ? `~${balance.toFixed(2)}` : balance.toFixed(2)

  if (isEstimate) {
    // 估算值：显示带提示的文本
    return (
      <Tooltip
        label="此为估算余额，基于总授予额度和已使用量计算。实际余额可能有所不同。"
        placement="top"
      >
        {/* 使用虚线样式和帮助光标，提示用户可以查看详细信息 */}
        <Text as="span" cursor="help" textDecoration="underline" textDecorationStyle="dotted">
          {displayBalance}
        </Text>
      </Tooltip>
    )
  }

  // 精确值：直接显示
  return <Text as="span">{displayBalance}</Text>
}
