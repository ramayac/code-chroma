/**
 * Task management system for project collaboration
 * Provides functionality for creating, updating, and managing tasks
 */

class Task {
    constructor(title, description, assignee = null, priority = 'medium') {
        this.id = this.generateId();
        this.title = title;
        this.description = description;
        this.assignee = assignee;
        this.priority = priority;
        this.status = 'pending';
        this.createdAt = new Date();
        this.updatedAt = new Date();
        this.dueDate = null;
        this.tags = [];
        this.comments = [];
    }

    generateId() {
        return '_' + Math.random().toString(36).substr(2, 9);
    }

    updateStatus(newStatus) {
        const validStatuses = ['pending', 'in-progress', 'completed', 'cancelled'];
        if (validStatuses.includes(newStatus)) {
            this.status = newStatus;
            this.updatedAt = new Date();
            return true;
        }
        return false;
    }

    addComment(comment, author) {
        this.comments.push({
            id: this.generateId(),
            text: comment,
            author: author,
            timestamp: new Date()
        });
        this.updatedAt = new Date();
    }

    setDueDate(date) {
        this.dueDate = new Date(date);
        this.updatedAt = new Date();
    }

    addTag(tag) {
        if (!this.tags.includes(tag)) {
            this.tags.push(tag);
            this.updatedAt = new Date();
        }
    }

    removeTag(tag) {
        const index = this.tags.indexOf(tag);
        if (index > -1) {
            this.tags.splice(index, 1);
            this.updatedAt = new Date();
        }
    }

    toJSON() {
        return {
            id: this.id,
            title: this.title,
            description: this.description,
            assignee: this.assignee,
            priority: this.priority,
            status: this.status,
            createdAt: this.createdAt,
            updatedAt: this.updatedAt,
            dueDate: this.dueDate,
            tags: this.tags,
            comments: this.comments
        };
    }
}

class TaskManager {
    constructor() {
        this.tasks = new Map();
        this.filters = {
            status: null,
            assignee: null,
            priority: null,
            tags: []
        };
    }

    createTask(title, description, assignee, priority) {
        const task = new Task(title, description, assignee, priority);
        this.tasks.set(task.id, task);
        return task;
    }

    getTask(id) {
        return this.tasks.get(id);
    }

    updateTask(id, updates) {
        const task = this.tasks.get(id);
        if (!task) return false;

        Object.keys(updates).forEach(key => {
            if (key in task && key !== 'id') {
                task[key] = updates[key];
            }
        });
        task.updatedAt = new Date();
        return true;
    }

    deleteTask(id) {
        return this.tasks.delete(id);
    }

    getAllTasks() {
        return Array.from(this.tasks.values());
    }

    getTasksByStatus(status) {
        return this.getAllTasks().filter(task => task.status === status);
    }

    getTasksByAssignee(assignee) {
        return this.getAllTasks().filter(task => task.assignee === assignee);
    }

    getTasksByPriority(priority) {
        return this.getAllTasks().filter(task => task.priority === priority);
    }

    searchTasks(query) {
        const lowercaseQuery = query.toLowerCase();
        return this.getAllTasks().filter(task => 
            task.title.toLowerCase().includes(lowercaseQuery) ||
            task.description.toLowerCase().includes(lowercaseQuery) ||
            task.tags.some(tag => tag.toLowerCase().includes(lowercaseQuery))
        );
    }

    getOverdueTasks() {
        const now = new Date();
        return this.getAllTasks().filter(task => 
            task.dueDate && task.dueDate < now && task.status !== 'completed'
        );
    }

    getTaskStatistics() {
        const tasks = this.getAllTasks();
        const stats = {
            total: tasks.length,
            pending: 0,
            'in-progress': 0,
            completed: 0,
            cancelled: 0,
            overdue: this.getOverdueTasks().length
        };

        tasks.forEach(task => {
            stats[task.status]++;
        });

        return stats;
    }

    exportTasks(format = 'json') {
        const tasks = this.getAllTasks();
        
        if (format === 'json') {
            return JSON.stringify(tasks, null, 2);
        } else if (format === 'csv') {
            const headers = ['ID', 'Title', 'Description', 'Assignee', 'Priority', 'Status', 'Created', 'Due Date'];
            const rows = tasks.map(task => [
                task.id,
                task.title,
                task.description,
                task.assignee || '',
                task.priority,
                task.status,
                task.createdAt.toISOString(),
                task.dueDate ? task.dueDate.toISOString() : ''
            ]);
            
            return [headers, ...rows].map(row => row.join(',')).join('\n');
        }
    }
}

// Utility functions
function priorityComparator(a, b) {
    const priorityOrder = { 'high': 3, 'medium': 2, 'low': 1 };
    return priorityOrder[b.priority] - priorityOrder[a.priority];
}

function dateComparator(a, b) {
    return new Date(b.createdAt) - new Date(a.createdAt);
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Task, TaskManager, priorityComparator, dateComparator };
}

// Global task manager instance
const taskManager = new TaskManager();
