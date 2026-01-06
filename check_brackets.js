const fs = require('fs');
const path = require('path');

// 读取HTML文件
const htmlFilePath = 'f:\\资料整理网站\\templates\\training_materials.html';
const htmlContent = fs.readFileSync(htmlFilePath, 'utf8');

// 提取所有script标签中的JavaScript代码
function extractJavaScript(html) {
    const scriptRegex = /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi;
    let scripts = [];
    let match;
    while ((match = scriptRegex.exec(html)) !== null) {
        scripts.push({
            code: match[0],
            index: match.index
        });
    }
    return scripts;
}

// 检查括号匹配
function checkBrackets(code, scriptIndex) {
    const braceStack = []; // 用于跟踪大括号 { }
    const parenStack = []; // 用于跟踪圆括号 ( )
    const lineNumbers = [];
    
    let currentLine = 1;
    for (let i = 0; i < code.length; i++) {
        if (code[i] === '\n') {
            currentLine++;
        }
        
        if (code[i] === '{') {
            braceStack.push({ char: '{', line: currentLine, position: i });
        } else if (code[i] === '}') {
            if (braceStack.length > 0) {
                const opening = braceStack.pop();
                lineNumbers.push({ opening: opening.line, closing: currentLine });
            } else {
                console.error(`在第${scriptIndex + 1}个script标签，第${currentLine}行发现多余的右花括号 }`);
            }
        } else if (code[i] === '(') {
            parenStack.push({ char: '(', line: currentLine, position: i });
        } else if (code[i] === ')') {
            if (parenStack.length > 0) {
                parenStack.pop();
            } else {
                console.error(`在第${scriptIndex + 1}个script标签，第${currentLine}行发现多余的右圆括号 )`);
            }
        }
    }
    
    // 检查是否有未闭合的括号
    if (braceStack.length > 0) {
        console.error(`在第${scriptIndex + 1}个script标签中发现${braceStack.length}个未闭合的左花括号 {`);
        braceStack.forEach(item => {
            console.error(`  在第${item.line}行`);
        });
    }
    
    if (parenStack.length > 0) {
        console.error(`在第${scriptIndex + 1}个script标签中发现${parenStack.length}个未闭合的左圆括号 (`);
        parenStack.forEach(item => {
            console.error(`  在第${item.line}行`);
        });
    }
    
    return {
        braceMismatch: braceStack.length > 0 || braceStack.length !== lineNumbers.length,
        parenMismatch: parenStack.length > 0
    };
}

// 按行分析JavaScript代码，寻找潜在问题
function analyzeJavaScriptByLine(code, scriptIndex) {
    const lines = code.split('\n');
    
    console.log(`\n分析第${scriptIndex + 1}个script标签:`);
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmedLine = line.trim();
        
        // 检查常见的语法错误模式
        if (trimmedLine.includes('} else') || trimmedLine.includes('}else')) {
            console.log(`  第${i + 1}行: 发现条件语句结构: ${trimmedLine}`);
        }
        
        if (trimmedLine === '}' || trimmedLine === '{') {
            console.log(`  第${i + 1}行: 单独的大括号: ${trimmedLine}`);
        }
        
        if (trimmedLine.startsWith('else {') || trimmedLine.startsWith('else{')) {
            console.log(`  第${i + 1}行: else语句: ${trimmedLine}`);
        }
        
        // 检查多余的右括号
        if (trimmedLine.endsWith('))') || trimmedLine.includes(')));')) {
            console.log(`  第${i + 1}行: 可能多余的右圆括号: ${trimmedLine}`);
        }
    }
}

// 主函数
function main() {
    const scripts = extractJavaScript(htmlContent);
    console.log(`找到${scripts.length}个script标签\n`);
    
    scripts.forEach((script, index) => {
        console.log(`\n=== 检查第${index + 1}个script标签 ===`);
        const result = checkBrackets(script.code, index);
        analyzeJavaScriptByLine(script.code, index);
        
        if (!result.braceMismatch && !result.parenMismatch) {
            console.log(`  第${index + 1}个script标签括号匹配正常`);
        }
    });
}

// 运行主函数
main();