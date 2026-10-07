/**
 * esbuild plugin to provide virtual modules for shadcn/ui components.
 * This allows generated code to import from '@/components/ui/*' paths.
 */

import type { Plugin } from 'esbuild';

/**
 * Inline shadcn component implementations.
 * These are bundled directly into the generated code.
 */
const SHADCN_UTILS = `
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
`;

const SHADCN_BUTTON = `
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export const Button = React.forwardRef(
  ({ className, variant = 'default', size = 'default', asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';

    const variantClasses = {
      default: 'bg-primary text-primary-foreground hover:bg-primary/90',
      destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
      outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
      secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
      ghost: 'hover:bg-accent hover:text-accent-foreground',
      link: 'text-primary underline-offset-4 hover:underline',
    };

    const sizeClasses = {
      default: 'h-10 px-4 py-2',
      sm: 'h-9 rounded-md px-3',
      lg: 'h-11 rounded-md px-8',
      icon: 'h-10 w-10',
    };

    return (
      <Comp
        className={cn(
          'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';
`;

const SHADCN_CARD = `
import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export const Card = React.forwardRef(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('rounded-lg border bg-card text-card-foreground shadow-sm', className)}
      {...props}
    />
  )
);
Card.displayName = 'Card';

export const CardHeader = React.forwardRef(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />
  )
);
CardHeader.displayName = 'CardHeader';

export const CardTitle = React.forwardRef(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn('text-2xl font-semibold leading-none tracking-tight', className)} {...props} />
  )
);
CardTitle.displayName = 'CardTitle';

export const CardDescription = React.forwardRef(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-sm text-muted-foreground', className)} {...props} />
  )
);
CardDescription.displayName = 'CardDescription';

export const CardContent = React.forwardRef(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
  )
);
CardContent.displayName = 'CardContent';

export const CardFooter = React.forwardRef(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center p-6 pt-0', className)} {...props} />
  )
);
CardFooter.displayName = 'CardFooter';
`;

const SHADCN_BADGE = `
import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function Badge({ className, variant = 'default', ...props }) {
  const variantClasses = {
    default: 'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
    secondary: 'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
    destructive: 'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
    outline: 'text-foreground',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}
`;

const SHADCN_SEPARATOR = `
import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export const Separator = React.forwardRef(
  ({ className, orientation = 'horizontal', decorative = true, ...props }, ref) => (
    <div
      ref={ref}
      role={decorative ? 'none' : 'separator'}
      aria-orientation={orientation}
      className={cn(
        'shrink-0 bg-border',
        orientation === 'horizontal' ? 'h-[1px] w-full' : 'h-full w-[1px]',
        className
      )}
      {...props}
    />
  )
);
Separator.displayName = 'Separator';
`;

/**
 * Virtual module content for shadcn components.
 */
export function createVirtualModulesPlugin(): Plugin {
  const componentMap: Record<string, string> = {
    button: SHADCN_BUTTON,
    card: SHADCN_CARD,
    badge: SHADCN_BADGE,
    separator: SHADCN_SEPARATOR,
  };

  return {
    name: 'virtual-modules',
    setup(build) {
      // Intercept imports to @/components/ui/*
      build.onResolve({ filter: /^@\/components\/ui\// }, (args) => {
        const componentName = args.path.replace('@/components/ui/', '');
        return {
          path: args.path,
          namespace: 'shadcn-virtual',
          pluginData: { componentName },
        };
      });

      // Intercept imports to @/lib/utils
      build.onResolve({ filter: /^@\/lib\/utils$/ }, (args) => {
        return {
          path: args.path,
          namespace: 'shadcn-virtual',
          pluginData: { isUtils: true },
        };
      });

      // Provide the virtual module content
      build.onLoad({ filter: /.*/, namespace: 'shadcn-virtual' }, async (args) => {
        const { componentName, isUtils } = args.pluginData as { componentName?: string; isUtils?: boolean };

        // If it's the utils module
        if (isUtils) {
          return {
            contents: SHADCN_UTILS,
            loader: 'tsx',
            resolveDir: process.cwd(), // Allow resolving node_modules
          };
        }

        // Get component source
        const componentSource = componentMap[componentName || ''];
        if (!componentSource) {
          return {
            errors: [
              {
                text: `Unknown shadcn component: ${componentName}. Available: ${Object.keys(componentMap).join(', ')}`,
              },
            ],
          };
        }

        return {
          contents: componentSource,
          loader: 'tsx',
          resolveDir: process.cwd(), // Allow resolving node_modules
        };
      });
    },
  };
}
