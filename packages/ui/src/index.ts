import React from 'react';

/**
 * UI 组件库入口
 *
 * P0 阶段仅提供基础类型定义
 * P4 阶段逐步添加 shadcn/ui 组件导出
 */

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'secondary' | 'destructive' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

export interface CardProps {
  children: React.ReactNode;
  className?: string;
}

// P0 占位导出
export const Button: React.FC<ButtonProps> = ({ children, ...props }) => {
  return <button {...props}>{children}</button>;
};

export const Card: React.FC<CardProps> = ({ children, className }) => {
  return <div className={className}>{children}</div>;
};
