const fs = require('fs');
const path = require('path');

// 读取文件内容
function readFile(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf8');
  } catch (error) {
    console.error('读取文件失败:', error.message);
    return null;
  }
}

// 提取JavaScript代码块
function extractJavaScriptBlocks(htmlContent) {
  const scriptTagRegex = /<script[^>]*>([\s\S]*?)<\/script>/g;
  const blocks = [];
  let match;
  
  while ((match = scriptTagRegex.exec(htmlContent)) !== null) {
    blocks.push(match[1]);
  }
  
  return blocks;
}

// 检查花括号和括号匹配情况
function checkBracesAndParens(jsCode, blockIndex) {
  let openBraces = 0;
  let closeBraces = 0;
  let openParens = 0;
  let closeParens = 0;
  let lineNumber = 1;
  const lineInfo = [];
  
  for (let i = 0; i < jsCode.length; i++) {
    if (jsCode[i] === '\n') {
      lineNumber++;
    }
    
    if (jsCode[i] === '{') {
      openBraces++;
    } else if (jsCode[i] === '}') {
      closeBraces++;
    } else if (jsCode[i] === '(') {
      openParens++;
    } else if (jsCode[i] === ')') {
      closeParens++;
    }
    
    // 记录每行的括号数量
    if (jsCode[i] === '\n' || i === jsCode.length - 1) {
      lineInfo.push({
        line: lineNumber,
        openBraces,
        closeBraces,
        braceBalance: openBraces - closeBraces,
        openParens,
        closeParens,
        parenBalance: openParens - closeParens
      });
    }
  }
  
  console.log(`\nJavaScript代码块 ${blockIndex + 1} 检查:`);
  console.log(`花括号统计: 打开 ${openBraces} 个, 关闭 ${closeBraces} 个, 差值: ${openBraces - closeBraces}`);
  console.log(`括号统计: 打开 ${openParens} 个, 关闭 ${closeParens} 个, 差值: ${openParens - closeParens}`);
  
  // 按行分析括号变化
  console.log('\n每行括号变化情况:');
  const lines = jsCode.split('\n');
  let braceStack = [];
  let parenStack = [];
  let braceChange = 0;
  let parenChange = 0;
  
  lines.forEach((line, lineIndex) => {
    const actualLineNum = lineIndex + 1;
    let lineBraceChange = 0;
    let lineParenChange = 0;
    
    for (let i = 0; i < line.length; i++) {
      if (line[i] === '{') {
        braceStack.push(actualLineNum);
        lineBraceChange++;
      } else if (line[i] === '}') {
        if (braceStack.length > 0) {
          braceStack.pop();
        }
        lineBraceChange--;
      } else if (line[i] === '(') {
        parenStack.push(actualLineNum);
        lineParenChange++;
      } else if (line[i] === ')') {
        if (parenStack.length > 0) {
          parenStack.pop();
        }
        lineParenChange--;
      }
    }
    
    braceChange += lineBraceChange;
    parenChange += lineParenChange;
    
    // 显示有变化的行
    if (lineBraceChange !== 0 || lineParenChange !== 0) {
      console.log(`  第${actualLineNum}行: 花括号变化 ${lineBraceChange > 0 ? '+' : ''}${lineBraceChange}, 括号变化 ${lineParenChange > 0 ? '+' : ''}${lineParenChange}`);
      console.log(`    当前平衡: 花括号=${braceChange}, 括号=${parenChange}`);
    }
  });
  
  // 显示未闭合的花括号
  if (braceStack.length > 0) {
    console.log('\n未闭合的左花括号位置:');
    braceStack.forEach((lineNum, index) => {
      console.log(`  第${lineNum}行 - 可能缺少对应的右花括号`);
    });
  }
  
  // 显示未闭合的括号
  if (parenStack.length > 0) {
    console.log('\n未闭合的左括号位置:');
    parenStack.forEach((lineNum, index) => {
      console.log(`  第${lineNum}行 - 可能缺少对应的右括号`);
    });
  }
  
  // 打印代码块的最后50行
  console.log('\n代码块最后50行:');
  lines.slice(-50).forEach((line, index) => {
    console.log(`${lines.length - 50 + index + 1}: ${line}`);
  });
  
  return {
    openBraces, 
    closeBraces, 
    braceDifference: openBraces - closeBraces,
    openParens,
    closeParens,
    parenDifference: openParens - closeParens
  };
}

// 主函数
function main() {
  const filePath = path.join(__dirname, 'templates', 'training_materials.html');
  const htmlContent = readFile(filePath);
  
  if (!htmlContent) {
    return;
  }
  
  const jsBlocks = extractJavaScriptBlocks(htmlContent);
  
  console.log(`发现 ${jsBlocks.length} 个JavaScript代码块`);
  
  jsBlocks.forEach((block, index) => {
    checkBracesAndParens(block, index);
  });
}

main();