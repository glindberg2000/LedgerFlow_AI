import { spawn } from 'child_process';

interface GrokOptions {
  model?: string;
  context_dir?: string;
}

interface GrokResult {
  content: string;
  error?: string;
}

export async function callGrok(
  prompt: string,
  options: GrokOptions = {}
): Promise<GrokResult> {
  const { model = 'grok-4-latest', context_dir } = options;
  
  // Build command arguments
  const args = ['-p', prompt, '-m', model];
  
  // Add directory context if provided
  if (context_dir) {
    args.unshift('-d', context_dir);
  }
  
  console.error('Calling Grok CLI:', JSON.stringify({ command: 'grok', args }));
  
  return new Promise((resolve) => {
    const child = spawn('grok', args, {
      env: {
        ...process.env,
        GROK_API_KEY: process.env.GROK_API_KEY
      },
      stdio: ['pipe', 'pipe', 'pipe']
    });
    
    let stdout = '';
    let stderr = '';
    
    child.stdout?.on('data', (data) => {
      stdout += data.toString();
    });
    
    child.stderr?.on('data', (data) => {
      stderr += data.toString();
    });
    
    // Set timeout for 2 minutes
    const timeout = setTimeout(() => {
      child.kill('SIGTERM');
      resolve({
        content: 'Grok CLI timed out (2 minutes)',
        error: 'timeout'
      });
    }, 120000);
    
    child.on('close', (code) => {
      clearTimeout(timeout);
      
      if (code === 0 && stdout.trim()) {
        // Success case
        const output = stdout.trim();
        
        // Try to parse JSON response if it looks like JSON
        try {
          const lines = output.split('\n');
          let content = '';
          
          // Look for assistant content in JSON format
          for (const line of lines) {
            if (line.trim().startsWith('{"role":"assistant"')) {
              const parsed = JSON.parse(line);
              if (parsed.content) {
                content += parsed.content + '\n';
              }
            } else if (line.trim() && !line.trim().startsWith('{"role":"user"')) {
              // Non-JSON text output
              content += line + '\n';
            }
          }
          
          if (content.trim()) {
            resolve({
              content: `**Grok Analysis (${model})**\n\n${content.trim()}`
            });
          } else {
            // Fallback to raw output
            resolve({
              content: `**Grok Analysis (${model})**\n\n${output}`
            });
          }
        } catch (e) {
          // Not JSON, treat as plain text
          resolve({
            content: `**Grok Analysis (${model})**\n\n${output}`
          });
        }
      } else {
        // Error case
        let errorMessage = `Grok CLI failed (exit code ${code})`;
        
        if (stderr.trim()) {
          errorMessage += `\nError: ${stderr.trim()}`;
        }
        
        if (stdout.trim()) {
          errorMessage += `\nOutput: ${stdout.trim()}`;
        }
        
        // Check for common error patterns
        if (stderr.includes('command not found') || stderr.includes('grok: not found')) {
          errorMessage = 'Error: Grok CLI not found. Please install the Grok CLI tool first.';
        } else if (stderr.includes('API key') || stderr.includes('authentication')) {
          errorMessage = 'Error: Grok API authentication failed. Please check your GROK_API_KEY.';
        }
        
        resolve({
          content: errorMessage,
          error: 'cli_error'
        });
      }
    });
    
    child.on('error', (error) => {
      clearTimeout(timeout);
      
      let errorMessage = `Grok CLI error: ${error.message}`;
      
      if (error.message.includes('ENOENT')) {
        errorMessage = 'Error: Grok CLI not found. Please install the Grok CLI tool first.';
      }
      
      resolve({
        content: errorMessage,
        error: 'spawn_error'
      });
    });
  });
}