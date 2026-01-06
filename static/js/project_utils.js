// 项目管理相关的JavaScript工具函数

// 存储当前选中的项目数据
let currentProject = null;

// 预先声明函数以确保可以提前暴露
function closeProjectDetails() {}
function confirmDelete(projectId, projectName) {}
function showProjectDetails(projectId) {}
function showModal(modalId) {}
function toggleDropdown(event, projectId) {}
function batchDeleteProjects() {}
function updateBatchDeleteButton() {}
function initProjectManagement() {}

// 提前将函数暴露到window对象，确保在任何时候都可用
window.showProjectDetails = showProjectDetails;
window.closeProjectDetails = closeProjectDetails;
window.confirmDelete = confirmDelete;
window.showModal = showModal;
window.toggleDropdown = toggleDropdown;
window.batchDeleteProjects = batchDeleteProjects;
window.updateBatchDeleteButton = updateBatchDeleteButton;
window.initProjectManagement = initProjectManagement;

// 关闭项目详细信息窗口
function closeProjectDetails() {
    const modal = document.getElementById('projectDetailsModal');
    const backdrop = document.getElementById('modalBackdrop');
    
    if (!modal || !backdrop) {
        console.error('关闭模态框时未找到相关元素');
        return;
    }
    
    // 添加淡出效果
    modal.classList.remove('show');
    backdrop.classList.remove('show');
    
    // 移除modal-open类
    document.body.classList.remove('modal-open');
    
    // 延迟隐藏以完成动画
    setTimeout(() => {
        modal.style.display = 'none';
        backdrop.style.display = 'none';
        window.currentProject = null;
    }, 300);
}

// 删除确认函数
function confirmDelete(projectId, projectName) {
    if (confirm('确定要删除项目 "' + projectName + '" 吗？此操作不可撤销。')) {
        window.location.href = '/project_management/delete_project/' + projectId;
    }
}

// 显示项目详情函数
function showProjectDetails(projectId) {
    console.log('====== 详细按钮点击事件触发 ======');
    console.log('项目ID:', projectId, '类型:', typeof projectId);
    
    try {
        console.log('开始执行showProjectDetails函数');
        
        let currentProject = null;
        
        // 1. 首先尝试从卡片视图获取项目数据（优先考虑卡片视图）
        console.log('尝试从卡片视图获取项目数据');
        
        // 尝试多种选择器获取卡片元素
        let projectCard = null;
        
        // 方法1：通过详情按钮查找
        const detailButton = document.querySelector(`.view-project-details[data-project-id="${projectId}"]`);
        if (detailButton) {
            projectCard = detailButton.closest('.product-card, .project-card, .card-item');
        }
        
        // 方法2：直接通过数据属性查找 - 增加更多可能的选择器
        if (!projectCard) {
            projectCard = document.querySelector(`.product-card[data-project-id="${projectId}"], .project-card[data-project-id="${projectId}"], .card-item[data-project-id="${projectId}"], [data-project-id="${projectId}"]`);
        }
        
        // 方法3：通过详情按钮中包含的卡片查找
        if (!projectCard) {
            const detailsButtons = document.querySelectorAll('.view-project-details');
            detailsButtons.forEach(btn => {
                if (btn.getAttribute('data-project-id') === projectId.toString()) {
                    const card = btn.closest('.product-card, .project-card, .card-item');
                    if (card) projectCard = card;
                }
            });
        }
        
        // 方法4：尝试通过按钮点击事件查找
        if (!projectCard && window.event && window.event.currentTarget) {
            console.log('通过事件目标查找卡片');
            const eventTarget = window.event.currentTarget;
            projectCard = eventTarget.closest('.product-card, .project-card, .card-item, [data-project-id]');
        }
        
        // 如果找到卡片元素，从卡片中提取项目信息
        if (projectCard) {
            console.log('找到项目卡片，提取项目信息');
            
            // 从卡片中提取项目信息 - 支持更多可能的选择器
            const projectName = (
                projectCard.querySelector('.product-title, .card-title, h5, h4, h3, .project-name, .title')?.textContent.trim() ||
                '未命名项目'
            );
            
            const projectType = (
                projectCard.querySelector('.project-type-badge, .project-type, .type, .category, [data-field="type"]')?.textContent.trim() ||
                '未设置类型'
            );
            
            const projectPrice = (
                projectCard.querySelector('.price-value, .project-price, .price, .amount, [data-field="price"]')?.textContent.trim() ||
                '0'
            );
            
            // 查找负责人信息 - 增强查找逻辑
            let assignedEngineer = '未分配';
            
            // 方法1：通过特定标签查找 - 增加更多可能的选择器
            const engineerSelectors = ['.product-info .product-info-value', '.project-engineer', '.engineer', '.responsible', '.person-in-charge', '[data-field="engineer"]'];
            for (const selector of engineerSelectors) {
                const engineerElement = projectCard.querySelector(selector);
                if (engineerElement && engineerElement.textContent.trim()) {
                    assignedEngineer = engineerElement.textContent.trim();
                    break;
                }
            }
            
            // 方法2：通过包含'负责人'文本的行查找
            if (assignedEngineer === '未分配') {
                const infoLines = projectCard.querySelectorAll('.product-info, div, span');
                for (const line of infoLines) {
                    if (line.textContent && (line.textContent.includes('负责人') || line.textContent.includes('工程师'))) {
                        const value = line.querySelector('.product-info-value')?.textContent.trim() || line.textContent.trim();
                        if (value) {
                            assignedEngineer = value.replace(/[工程师负责人负责:：]/g, '').trim();
                            break;
                        }
                    }
                }
            }
            
            // 获取项目群组信息
            const projectGroup = (
                projectCard.querySelector('.project-group, .group, .team, [data-field="group"]')?.textContent.trim() ||
                '未设置'
            );
            
            // 获取项目成本信息
            const projectCost = (
                projectCard.querySelector('.project-cost, .cost, [data-field="cost"]')?.textContent.trim() ||
                '未设置'
            );
            
            // 获取项目单价信息
            const projectUnitPrice = (
                projectCard.querySelector('.project-unit-price, .unit-price, [data-field="unit_price"]')?.textContent.trim() ||
                '未设置'
            );
            
            // 获取标签信息 - 支持多种可能的选择器
            const tags = [];
            const tagElements = projectCard.querySelectorAll('.tag-container .tag, .project-tag, .tag, .badge, .label');
            tagElements.forEach(tag => {
                // 跳过计数标签（如 +2）
                const tagText = tag.textContent.trim();
                if (!tagText.startsWith('+') && tagText) {
                    tags.push(tagText);
                }
            });
            
            // 如果没有找到标签元素，尝试从文本内容中提取
            if (tags.length === 0) {
                const tagsElement = projectCard.querySelector('[data-field="tags"]');
                if (tagsElement) {
                    const tagsText = tagsElement.textContent.trim();
                    if (tagsText) {
                        // 支持多种分隔符
                        tags.push(...tagsText.split(/[,，;；]/).map(t => t.trim()).filter(Boolean));
                    }
                }
            }
            
            // 获取日期信息 - 增强查找逻辑
            let dateInfo = '';
            const dateSelectors = ['.product-date', '.project-date', '.date', 'time', '.create-time', '.update-time', '[data-field="date"]'];
            for (const selector of dateSelectors) {
                const dateElement = projectCard.querySelector(selector);
                if (dateElement && dateElement.textContent.trim()) {
                    dateInfo = dateElement.textContent.trim();
                    break;
                }
            }
            
            // 如果没找到，尝试查找包含日期格式的文本
            if (!dateInfo) {
                const textContents = projectCard.innerText;
                // 增强的日期格式匹配
                const dateMatch = textContents.match(/\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|\d{4}年\d{1,2}月\d{1,2}日/);
                if (dateMatch) {
                    dateInfo = dateMatch[0];
                }
            }
            
            // 构建项目数据对象
            currentProject = {
                id: projectId,
                name: projectName,
                project_type: projectType,
                price: projectPrice,
                assigned_engineer: assignedEngineer,
                group_name: projectGroup,
                cost: projectCost,
                unit_price: projectUnitPrice,
                tags: tags,
                date: dateInfo
            };
            
            console.log('从卡片获取的项目数据:', currentProject);
        }
        
        // 2. 如果卡片视图中没有找到，尝试从表格视图获取
        if (!currentProject) {
            console.log('卡片视图中未找到数据，尝试从表格视图获取');
            
            // 首先，直接为所有表格行添加data-project-id属性（如果尚未添加）
            document.querySelectorAll('tbody tr').forEach(row => {
                const idCell = row.querySelector('td:first-child + td'); // 获取ID列（复选框后面的列）
                if (idCell) {
                    const currentId = idCell.textContent.trim();
                    if (currentId) {
                        row.setAttribute('data-project-id', currentId);
                    }
                }
            });
            
            // 从表格中获取项目数据 - 增加更多可能的选择器
            const projectElements = document.querySelectorAll(`tr[data-project-id="${projectId}"], tr[id="project-${projectId}"]`);
            console.log('找到的表格元素数量:', projectElements.length);
            
            if (projectElements.length > 0) {
                const targetRow = projectElements[0];
                const cells = targetRow.querySelectorAll('td');
                
                // 根据实际表格结构确定正确的列索引（考虑是否有复选框列）
                const checkboxColExists = cells.length > 9 && cells[0].querySelector('input[type="checkbox"]');
                const idColIndex = checkboxColExists ? 1 : 0;
                const nameColIndex = checkboxColExists ? 2 : 1;
                const typeColIndex = checkboxColExists ? 3 : 2;
                const groupColIndex = checkboxColExists ? 4 : 3;
                const priceColIndex = checkboxColExists ? 5 : 4;
                const engineerColIndex = checkboxColExists ? 6 : 5;
                const tagsColIndex = checkboxColExists ? 7 : 6;
                const timeColIndex = checkboxColExists ? 8 : 7;
                const costColIndex = checkboxColExists ? 9 : 8;
                const unitPriceColIndex = checkboxColExists ? 10 : 9;
                
                // 构建项目数据对象
                currentProject = {
                    id: projectId,
                    name: cells[nameColIndex] ? cells[nameColIndex].textContent.trim() : '',
                    project_type: cells[typeColIndex] ? cells[typeColIndex].textContent.trim() : '',
                    price: cells[priceColIndex] ? cells[priceColIndex].textContent.trim() : '',
                    assigned_engineer: cells[engineerColIndex] ? cells[engineerColIndex].textContent.trim() : '',
                    group_name: cells[groupColIndex] ? cells[groupColIndex].textContent.trim() : '未设置',
                    cost: cells[costColIndex] ? cells[costColIndex].textContent.trim() : '未设置',
                    unit_price: cells[unitPriceColIndex] ? cells[unitPriceColIndex].textContent.trim() : '未设置',
                    tags: [],
                    date: ''
                };
                
                // 尝试提取标签
                if (cells[tagsColIndex]) {
                    const tagElements = cells[tagsColIndex].querySelectorAll('.tag, .badge');
                    if (tagElements.length > 0) {
                        tagElements.forEach(tag => {
                            const tagText = tag.textContent.trim();
                            if (tagText) currentProject.tags.push(tagText);
                        });
                    } else {
                        // 如果没有标签元素，尝试解析文本内容
                        const tagsText = cells[tagsColIndex].textContent.trim();
                        if (tagsText) {
                            currentProject.tags = tagsText.split(/[,，;；]/).map(t => t.trim()).filter(Boolean);
                        }
                    }
                }
                
                // 尝试提取日期
                if (cells[timeColIndex]) {
                    currentProject.date = cells[timeColIndex].textContent.trim();
                }
                
                console.log('从表格获取的项目数据:', currentProject);
            }
        }
        
        // 3. 如果仍然没有找到数据，创建基本信息
        if (!currentProject) {
            console.warn('找不到项目数据，创建基本信息');
            currentProject = {
                id: projectId,
                name: '项目详情',
                project_type: '未设置',
                price: '未设置',
                assigned_engineer: '未分配',
                group_name: '未设置',
                cost: '未设置',
                unit_price: '未设置',
                tags: [],
                date: ''
            };
        }
        
        // 尝试查找专门的项目详情模态框
            let modal = null;
            let isCustomModal = false;
            
            // 1. 优先查找专门的模态框
            modal = document.getElementById('projectDetailsModal');
            if (!modal && window.jQuery) {
                modal = $('#projectDetailsModal')[0];
            }
            
            // 2. 如果没有找到专门的模态框，创建临时模态框
            if (!modal) {
                console.log('未找到专门的模态框，创建临时模态框');
                
                // 检查是否已存在临时模态框，如有则移除
                var existingTempModal = document.getElementById('tempProjectDetailsModal');
                var existingTempBackdrop = document.getElementById('tempBackdrop');
                if (existingTempModal) existingTempModal.remove();
                if (existingTempBackdrop) existingTempBackdrop.remove();
                
                // 创建临时模态框 - 修复模板字符串语法问题
                // 先转义项目名称，避免引号导致的语法错误
                var escapedProjectName = (currentProject.name || '项目名称').replace(/'/g, '\\\'');
                
                // 构建标签HTML（如果有）
                var tagsHTML = '';
                if (currentProject.tags && currentProject.tags.length > 0) {
                    const tagElements = currentProject.tags.map(tag => `<span class="tag">${tag}</span>`).join(' ');
                    tagsHTML = '<div class="row mb-3">\n                        <div class="col-4"><strong>项目标签:</strong></div>\n                        <div class="col-8">' + tagElements + '</div>\n                    </div>';
                }
                
                // 构建时间HTML（如果有）
                var timeHTML = '';
                if (currentProject.date) {
                    timeHTML = '<div class="row mb-3">\n                        <div class="col-4"><strong>创建时间:</strong></div>\n                        <div class="col-8">' + currentProject.date + '</div>\n                    </div>';
                }
                
                // 构建删除按钮HTML（如果是超级管理员）
                var deleteBtnHTML = '';
                if (window.isSuperAdmin) {
                    deleteBtnHTML = '<button type="button" class="btn btn-danger mr-2" onclick="confirmDelete(' + projectId + ', \'' + escapedProjectName + '\')">删除项目</button>';
                }
                
                // 构建完整的模态框HTML
                var tempModalHTML = '<div id="tempProjectDetailsModal" class="modal fade show" style="display:block; z-index:1050;">' +
                    '<div class="modal-dialog modal-lg">' +
                        '<div class="modal-content">' +
                            '<div class="modal-header">' +
                                '<h5 class="modal-title">项目详情</h5>' +
                                '<button type="button" class="close" onclick="document.getElementById(\'tempProjectDetailsModal\').remove(); document.getElementById(\'tempBackdrop\').remove(); document.body.classList.remove(\'modal-open\');">&times;</button>' +
                            '</div>' +
                            '<div class="modal-body">' +
                                '<div class="container">' +
                                    '<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">' +
                                        '<div class="bg-white p-4 rounded-lg shadow-sm">' +
                                            '<div class="text-sm text-gray-500 mb-1">项目名称</div>' +
                                            '<div class="font-medium text-lg">' + (currentProject.name || '项目名称') + '</div>' +
                                        '</div>' +
                                        '<div class="bg-white p-4 rounded-lg shadow-sm">' +
                                            '<div class="text-sm text-gray-500 mb-1">项目ID</div>' +
                                            '<div class="font-medium">' + currentProject.id + '</div>' +
                                        '</div>' +
                                    '</div>' +
                                    '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">' +
                                        '<div class="bg-white p-4 rounded-lg shadow-sm">' +
                                            '<div class="text-sm text-gray-500 mb-1">项目类型</div>' +
                                            '<div class="font-medium">' + (currentProject.project_type || '未设置') + '</div>' +
                                        '</div>' +
                                        '<div class="bg-white p-4 rounded-lg shadow-sm">' +
                                            '<div class="text-sm text-gray-500 mb-1">项目价格</div>' +
                                            '<div class="font-medium">' + (currentProject.price || '未设置') + '</div>' +
                                        '</div>' +
                                        '<div class="bg-white p-4 rounded-lg shadow-sm">' +
                                            '<div class="text-sm text-gray-500 mb-1">项目负责人</div>' +
                                            '<div class="font-medium">' + (currentProject.assigned_engineer || '未分配') + '</div>' +
                                        '</div>' +
                                    '</div>' +
                                    '<div class="bg-white p-4 rounded-lg shadow-sm mb-4">' +
                                        '<div class="text-sm text-gray-500 mb-1">所属群组</div>' +
                                        '<div class="font-medium">' + (currentProject.group_name || '未设置') + '</div>' +
                                    '</div>' +
                                    tagsHTML +
                                    timeHTML +
                                '</div>' +
                            '</div>' +
                            '<div class="modal-footer">' +
                                '<a href="/project_management/edit_project/' + projectId + '" class="btn btn-primary mr-2">编辑项目</a>' +
                                deleteBtnHTML +
                                '<button type="button" class="btn btn-secondary" onclick="document.getElementById(\'tempProjectDetailsModal\').remove(); document.getElementById(\'tempBackdrop\').remove(); document.body.classList.remove(\'modal-open\');">关闭</button>' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
                '</div>' +
                '<div id="tempBackdrop" class="modal-backdrop fade show" style="z-index:1040;"></div>';
                
                const tempContainer = document.createElement('div');
                tempContainer.innerHTML = tempModalHTML;
                document.body.appendChild(tempContainer);
                document.body.classList.add('modal-open');
                isCustomModal = true;
                
                console.log('临时模态框创建成功');
                return; // 直接返回，因为我们已经显示了临时模态框
            }
            
            // 3. 如果找到了专门的模态框，使用我们优化的网格布局替换原有内容
            console.log('找到了项目详情模态框，使用优化的网格布局样式');
            
            // 获取背景遮罩
            let backdrop = document.getElementById('modalBackdrop');
            
            // 使用我们优化的网格布局替换原有模态框内容
            try {
                // 尝试从表格中获取成本和单价信息
                let costValue = '未设置';
                let unitPriceValue = '未设置';
                
                // 如果有隐藏的成本和单价列，尝试获取
                const hiddenCostElement = document.querySelector(`[data-project-id="${projectId}"] [data-field="cost"]`);
                const hiddenUnitPriceElement = document.querySelector(`[data-project-id="${projectId}"] [data-field="unit_price"]`);
                
                if (hiddenCostElement) {
                    costValue = hiddenCostElement.textContent.trim() || '未设置';
                }
                
                if (hiddenUnitPriceElement) {
                    unitPriceValue = hiddenUnitPriceElement.textContent.trim() || '未设置';
                }
                
                // 更新currentProject对象
                currentProject.cost = costValue;
                currentProject.unit_price = unitPriceValue;
                
                // 构建标签HTML（使用currentProject中的tags数组）
                let tagsHTML = '';
                if (currentProject.tags && currentProject.tags.length > 0) {
                    const tagsContent = currentProject.tags.map(tag => 
                        `<span class="tag">${tag}</span>`
                    ).join(' ');
                    tagsHTML = `<tr>
                        <td class="font-weight-bold">项目标签</td>
                        <td><div class="d-flex flex-wrap gap-2">${tagsContent}</div></td>
                    </tr>`;
                }
                
                // 构建时间HTML（使用currentProject中的date）
                let timeHTML = '';
                if (currentProject.date) {
                    timeHTML = `<tr>
                        <td class="font-weight-bold">创建时间</td>
                        <td>${currentProject.date}</td>
                    </tr>`;
                }
                
                // 替换整个模态框body内容为表格形式（使用Bootstrap类）
                const modalBody = modal.querySelector('.modal-body');
                if (modalBody) {
                    modalBody.innerHTML = `
                    <div class="container">
                        <!-- 项目名称和ID区域 -->
                        <div class="mb-4 text-center">
                            <h3 class="mb-2">${currentProject.name || '项目名称'}</h3>
                            <p class="text-muted">ID: ${currentProject.id}</p>
                        </div>
                        
                        <!-- 项目信息表格 -->
                        <table class="table table-bordered table-hover">
                            <tbody>
                                <tr>
                                    <td class="font-weight-bold">项目类型</td>
                                    <td>${currentProject.project_type || '未设置'}</td>
                                </tr>
                                <tr>
                                    <td class="font-weight-bold">项目价格</td>
                                    <td>${currentProject.price || '未设置'}</td>
                                </tr>
                                <tr>
                                    <td class="font-weight-bold">项目成本</td>
                                    <td>${currentProject.cost || '未设置'}</td>
                                </tr>
                                <tr>
                                    <td class="font-weight-bold">项目单价</td>
                                    <td>${currentProject.unit_price || '未设置'}</td>
                                </tr>
                                <tr>
                                    <td class="font-weight-bold">项目负责人</td>
                                    <td>${currentProject.assigned_engineer || '未分配'}</td>
                                </tr>
                                <tr>
                                    <td class="font-weight-bold">所属群组</td>
                                    <td>${currentProject.group_name || '未设置'}</td>
                                </tr>
                                ${tagsHTML}
                                ${timeHTML}
                            </tbody>
                        </table>
                    </div>`;
                }
                
                // 保留原有操作按钮的逻辑
                const editLink = document.getElementById('editProjectLink');
                const uploadBtn = document.getElementById('uploadMaterialsBtn');
                const viewBtn = document.getElementById('viewMaterialsBtn');
                const deleteBtn = document.getElementById('deleteProjectBtn');
                
                if (editLink) {
                    editLink.href = '/project_management/edit_project/' + projectId;
                }
                
                if (uploadBtn) {
                    uploadBtn.onclick = function(e) {
                        if (e) e.stopPropagation();
                        // 使用全局上传模态框
                        if (window.openGlobalUploadModal) {
                            window.openGlobalUploadModal(projectId, currentProject.name);
                        }
                    };
                }
                
                if (viewBtn) {
                    viewBtn.onclick = function(e) {
                        if (e) e.stopPropagation();
                        // 使用全局查看资料模态框
                        if (window.openGlobalMaterialsModal) {
                            window.openGlobalMaterialsModal(projectId, currentProject.name);
                        }
                    };
                }
                
                // 显示/隐藏删除按钮
                if (deleteBtn) {
                    // 使用全局变量而不是直接嵌入模板标签
                    if (window.isSuperAdmin) {
                        deleteBtn.style.display = 'block';
                        deleteBtn.onclick = function(e) {
                            if (e) e.stopPropagation();
                            if (window.confirmDelete) {
                                window.confirmDelete(projectId, currentProject.name);
                            } else if (confirm(`确定要删除项目 "${currentProject.name}" 吗？此操作不可撤销。`)) {
                                window.location.href = '/project_management/delete_project/' + projectId;
                            }
                        };
                    } else {
                        deleteBtn.style.display = 'none';
                    }
                }
            } catch (fillError) {
                console.error('填充模态框内容时出错:', fillError);
                // 如果填充失败，仍然尝试显示模态框
            }
            
            // 显示模态框
            try {
                console.log('尝试显示模态框');
                
                // 如果没有背景遮罩，创建一个
                if (!backdrop) {
                    backdrop = document.createElement('div');
                    backdrop.id = 'modalBackdrop';
                    backdrop.className = 'modal-backdrop fade';
                    backdrop.style.display = 'none';
                    document.body.appendChild(backdrop);
                }
                
                // 显示模态框
                modal.style.display = 'block';
                backdrop.style.display = 'block';
                
                // 添加淡入效果
                setTimeout(function() {
                    modal.classList.add('show');
                    backdrop.classList.add('show');
                    document.body.classList.add('modal-open');
                }, 10);
                
                // 同时尝试jQuery方法
                if (window.jQuery) {
                    console.log('同时尝试jQuery方法显示模态框');
                    try {
                        $(modal).modal('show');
                    } catch (jqError) {
                        console.warn('jQuery模态框方法失败，但继续使用原生方法:', jqError);
                    }
                }
            } catch (showError) {
                console.error('显示模态框时出错:', showError);
                // 如果显示失败，创建临时模态框
                console.log('显示模态框失败，创建临时模态框作为备选方案');
                
                // 检查是否已存在临时模态框，如有则移除
                var existingTempModal = document.getElementById('tempProjectDetailsModal');
                var existingTempBackdrop = document.getElementById('tempBackdrop');
                if (existingTempModal) existingTempModal.remove();
                if (existingTempBackdrop) existingTempBackdrop.remove();
                
                // 创建临时模态框 - 修复模板字符串语法问题
                // 先转义项目名称，避免引号导致的语法错误
                var escapedProjectName = (currentProject.name || '项目名称').replace(/'/g, '\\\'');
                
                // 构建删除按钮HTML（如果是超级管理员）
                var deleteBtnHTML = '';
                if (window.isSuperAdmin) {
                    deleteBtnHTML = '<button type="button" class="btn btn-danger mr-2" onclick="confirmDelete(' + projectId + ', \'' + escapedProjectName + '\')">删除项目</button>';
                }
                
                // 构建完整的模态框HTML - 使用Bootstrap表格布局
                // 构建项目标签和创建时间的HTML（只使用currentProject中的数据）
                var tagsHTML = '';
                if (currentProject.tags && currentProject.tags.length > 0) {
                    const tagsContent = currentProject.tags.map(tag => 
                        `<span class="tag">${tag}</span>`
                    ).join(' ');
                    tagsHTML = '<tr><td class="font-weight-bold">项目标签</td><td><div class="d-flex flex-wrap gap-2">' + tagsContent + '</div></td></tr>';
                }
                
                var timeHTML = currentProject.date ? '<tr><td class="font-weight-bold">创建时间</td><td>' + currentProject.date + '</td></tr>' : '';
                
                var tempModalHTML = '<div id="tempProjectDetailsModal" class="modal fade show" style="display:block; z-index:1050;">' +
                    '<div class="modal-dialog modal-lg">' +
                        '<div class="modal-content">' +
                            '<div class="modal-header">' +
                                '<h5 class="modal-title">项目详情</h5>' +
                                '<button type="button" class="close" onclick="document.getElementById(\'tempProjectDetailsModal\').remove(); document.getElementById(\'tempBackdrop\').remove(); document.body.classList.remove(\'modal-open\');">&times;</button>' +
                            '</div>' +
                            '<div class="modal-body">' +
                                '<div class="container">' +
                                    '<div class="mb-4 text-center">' +
                                        '<h3 class="mb-2">' + (currentProject.name || '项目名称') + '</h3>' +
                                        '<p class="text-muted">ID: ' + currentProject.id + '</p>' +
                                    '</div>' +
                                    '<table class="table table-bordered table-hover">' +
                                        '<tbody>' +
                                            '<tr>' +
                                                '<td class="font-weight-bold">项目类型</td>' +
                                                '<td>' + (currentProject.project_type || '未设置') + '</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td class="font-weight-bold">项目价格</td>' +
                                                '<td>' + (currentProject.price || '未设置') + '</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td class="font-weight-bold">项目成本</td>' +
                                                '<td>' + (currentProject.cost || '未设置') + '</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td class="font-weight-bold">项目单价</td>' +
                                                '<td>' + (currentProject.unit_price || '未设置') + '</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td class="font-weight-bold">项目负责人</td>' +
                                                '<td>' + (currentProject.assigned_engineer || '未分配') + '</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td class="font-weight-bold">所属群组</td>' +
                                                '<td>' + (currentProject.group_name || '未设置') + '</td>' +
                                            '</tr>' +
                                            tagsHTML +
                                            timeHTML +
                                        '</tbody>' +
                                    '</table>' +
                                '</div>' +
                            '</div>' +
                            '<div class="modal-footer">' +
                                '<a href="/project_management/edit_project/' + projectId + '" class="btn btn-primary mr-2">编辑项目</a>' +
                                deleteBtnHTML +
                                '<button type="button" class="btn btn-secondary" onclick="document.getElementById(\'tempProjectDetailsModal\').remove(); document.getElementById(\'tempBackdrop\').remove(); document.body.classList.remove(\'modal-open\');">关闭</button>' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
                '</div>' +
                '<div id="tempBackdrop" class="modal-backdrop fade show" style="z-index:1040;"></div>';
                
                const tempContainer = document.createElement('div');
                tempContainer.innerHTML = tempModalHTML;
                document.body.appendChild(tempContainer);
                document.body.classList.add('modal-open');
            }
        }
    } catch (error) {
        console.error('====== 显示项目详情时出错 ======');
        console.error('错误对象:', error);
        console.error('错误类型:', error.name);
        console.error('错误消息:', error.message);
        console.error('错误堆栈:', error.stack);
        alert('显示项目详情时出错，请查看控制台获取详细信息');
    } finally {
        // 阻止事件冒泡
        if (window.event) {
            console.log('阻止事件冒泡');
            window.event.stopPropagation();
        }
        console.log('====== 函数执行完毕 ======');
    }
}

// 模态框显示函数
function showModal(modalId) {
    console.log('显示模态框:', modalId);
    
    // 首先尝试jQuery方法
    if (typeof $ !== 'undefined') {
        console.log('使用jQuery显示模态框:', modalId);
        $('#' + modalId).modal('show');
        return;
    }
    
    // 原生JavaScript方式作为备选
    var modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        document.body.classList.add('modal-open');
        
        // 添加淡入效果
        setTimeout(function() {
            modal.classList.add('show');
        }, 10);
    } else {
        console.error('找不到指定的模态框:', modalId);
    }
}

// 下拉菜单切换函数
function toggleDropdown(event, projectId) {
    event.preventDefault();
    event.stopPropagation();
    
    const menu = document.getElementById('dropdownMenu' + projectId);
    const isOpen = menu && menu.classList.contains('show');
    
    // 关闭所有下拉菜单
    document.querySelectorAll('.dropdown-menu').forEach(m => {
        m.classList.remove('show');
        m.style.display = 'none';
    });
    
    if (menu && !isOpen) {
        menu.style.display = 'block';
        setTimeout(() => {
            menu.classList.add('show');
        }, 10);
    }
}

// 批量删除功能
function batchDeleteProjects() {
    const selectedIds = [];
    document.querySelectorAll('.project-checkbox:checked').forEach(checkbox => {
        selectedIds.push(checkbox.value);
    });
    
    if (selectedIds.length > 0) {
        if (confirm(`确定要删除选中的 ${selectedIds.length} 个项目吗？此操作不可撤销。`)) {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/project_management/batch_delete_projects';
            
            const idsInput = document.createElement('input');
            idsInput.type = 'hidden';
            idsInput.name = 'project_ids';
            idsInput.value = JSON.stringify(selectedIds);
            form.appendChild(idsInput);
            
            document.body.appendChild(form);
            form.submit();
        }
    }
}

// 更新批量删除按钮状态
function updateBatchDeleteButton() {
    const checkedCount = document.querySelectorAll('.project-checkbox:checked').length;
    const countElement = document.getElementById('selectedCount');
    const deleteButton = document.getElementById('batchDeleteBtn');
    
    if (countElement) countElement.textContent = checkedCount;
    if (deleteButton) deleteButton.disabled = checkedCount === 0;
}

// 页面加载完成后执行的初始化
function initProjectManagement() {
    console.log('初始化项目管理功能...');
    
    // 立即将函数暴露到window对象，确保在DOM加载完成前也可用
    window.showProjectDetails = showProjectDetails;
    window.closeProjectDetails = closeProjectDetails;
    window.confirmDelete = confirmDelete;
    window.showModal = showModal;
    window.toggleDropdown = toggleDropdown;
    window.batchDeleteProjects = batchDeleteProjects;
    window.updateBatchDeleteButton = updateBatchDeleteButton;
    
    // 为表格行添加项目ID数据属性
    document.querySelectorAll('tbody tr').forEach(row => {
        const checkbox = row.querySelector('input[type="checkbox"]');
        if (checkbox && checkbox.value) {
            const projectId = checkbox.value;
            row.setAttribute('data-project-id', projectId);
        }
    });
    
    // 绑定背景点击事件
    const backdrop = document.getElementById('modalBackdrop');
    if (backdrop) {
        backdrop.addEventListener('click', closeProjectDetails);
    }
    
    console.log('项目管理初始化完成');
}

// 将函数暴露到全局作用域
// 页面加载完成后自动初始化
document.addEventListener('DOMContentLoaded', initProjectManagement);