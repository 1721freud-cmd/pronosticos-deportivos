// Configuración
const CONFIG = {
    updateInterval: 43200000, // 12 horas
    timeZone: 'America/Argentina/Buenos_Aires'
};

// Estado global
let allMatches = [];
let currentFilter = 'all';
let lastUpdateTime = null;

// Utilidades
const Utils = {
    getConfidenceBadge(match) {
        if (match.is_very_safe) {
            return '<span class="very-safe-badge px-2 py-1 rounded text-xs font-bold"><i class="fas fa-shield-alt mr-1"></i>MUY SEGURO</span>';
        } else if (match.is_clear_favorite) {
            return '<span class="favorite-badge px-2 py-1 rounded text-xs font-bold"><i class="fas fa-star mr-1"></i>FAVORITO</span>';
        } else if (match.is_risky) {
            return '<span class="risky-badge px-2 py-1 rounded text-xs font-bold"><i class="fas fa-exclamation-triangle mr-1"></i>RIESGOSO</span>';
        }
        return '';
    },

    getConfidenceColor(confidence) {
        if (confidence >= 75) return 'from-green-500 to-emerald-500';
        if (confidence >= 60) return 'from-blue-500 to-cyan-500';
        if (confidence >= 50) return 'from-yellow-500 to-orange-500';
        return 'from-red-500 to-pink-500';
    },

    getConfidenceTextColor(confidence) {
        if (confidence >= 75) return 'text-green-400';
        if (confidence >= 60) return 'text-blue-400';
        if (confidence >= 50) return 'text-yellow-400';
        return 'text-red-400';
    },

    formatTime(date) {
        return date.toLocaleTimeString('es-AR', {
            timeZone: CONFIG.timeZone,
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    formatRelativeTime(date) {
        const now = new Date();
        const diffMs = date - now;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays > 0) {
            return `hace ${diffDays} días`;
        } else if (diffHours > 0) {
            return `hace ${diffHours} horas`;
        } else if (diffMinutes > 0) {
            return `hace ${Math.floor(diffMinutes / 60)} minutos`;
        }
        return 'Ahora mismo';
    },

    showLoading(containerId) {
        document.getElementById(containerId).innerHTML = `
            <div class="loading-spinner mx-auto"></div>
        `;
    },

    showError(containerId, message) {
        document.getElementById(containerId).innerHTML = `
            <div class="col-span-full text-center py-12 text-red-400">
                <i class="fas fa-exclamation-triangle text-5xl mb-4"></i>
                <p class="text-lg">${message}</p>
            </div>
        `;
    }
};

// API
const API = {
    async fetch(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    async getMatches() {
        return this.fetch('/api/matches');
    },

    async getCombinada() {
        return this.fetch('/api/combinada');
    }
};

// Render
const Renderer = {
    updateStats(stats) {
        document.getElementById('today-count').textContent = stats.today_count || 0;
        document.getElementById('tomorrow-count').textContent = stats.tomorrow_count || 0;
        document.getElementById('favorites-count').textContent = stats.favorites || 0;
        document.getElementById('very-safe-count').textContent = stats.very_safe || 0;
        document.getElementById('avg-confidence').textContent = (stats.avg_confidence || 0) + '%';
        document.getElementById('last-update').textContent = Utils.formatTime(new Date());
    },

    renderCombinada(combinada) {
        const container = document.getElementById('combinada-container');

        if (combinada.length === 0) {
            container.innerHTML = `
                <div class="bg-white/5 backdrop-blur-sm rounded-xl p-8 border border-gray-700/30 text-center">
                    <i class="fas fa-info-circle text-5xl text-gray-500 mb-4"></i>
                    <p class="text-gray-400">No hay suficientes favoritos claros hoy</p>
                    <p class="text-sm text-gray-500 mt-2">Se requiere confianza ≥ 60%</p>
                </div>
            `;
            return;
        }

        container.innerHTML = combinada.map((match, index) => `
            <div class="combinada-card backdrop-blur-sm rounded-xl p-5 border border-yellow-500/30 card-glow fade-in" style="animation-delay: ${index * 0.1}s">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-3 flex-wrap">
                            <span class="bg-gradient-to-r from-yellow-500 to-orange-500 text-black px-3 py-1 rounded-lg text-sm font-bold">#${index + 1}</span>
                            <span class="text-gray-400 text-sm">${match.date} • ${match.time}</span>
                            ${match.is_today ? '<span class="bg-green-500/20 text-green-400 px-2 py-1 rounded text-xs font-medium">HOY</span>' : ''}
                            ${match.sport === 'football' ? '<i class="fas fa-futbol text-green-400"></i>' : '<i class="fas fa-basketball-ball text-orange-400"></i>'}
                            ${match.league ? `<span class="bg-blue-500/20 text-blue-400 px-2 py-1 rounded text-xs font-medium">${match.league}</span>` : ''}
                        </div>
                        <div class="flex items-center justify-between mb-4">
                            <div class="text-lg font-semibold">${match.home_team}</div>
                            <div class="text-gray-500 font-bold">VS</div>
                            <div class="text-lg font-semibold">${match.away_team}</div>
                        </div>
                        <div class="flex items-center gap-4">
                            <div class="flex-1">
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-sm text-gray-400">Confianza</span>
                                    <span class="text-2xl font-bold text-yellow-400">${match.confidence}%</span>
                                </div>
                                <div class="h-3 bg-gray-700 rounded-full overflow-hidden">
                                    <div class="confidence-bar h-full bg-gradient-to-r from-yellow-500 to-orange-500 rounded-full" style="width: ${match.confidence}%"></div>
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="text-sm text-gray-400">Pronóstico</div>
                                <div class="text-lg font-bold text-white">${match.prediction}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    },

    renderMatches() {
        const container = document.getElementById('matches-container');
        let filteredMatches = this.filterMatches(allMatches, currentFilter);

        if (filteredMatches.length === 0) {
            Utils.showError(container.id, 'No hay partidos disponibles con este filtro');
            return;
        }

        container.innerHTML = filteredMatches.map((match, index) => `
            <div class="bg-white/5 backdrop-blur-sm rounded-xl p-5 border border-gray-700/30 card-glow fade-in ${match.is_very_safe ? 'border-green-500/30' : match.is_clear_favorite ? 'border-blue-500/30' : ''}" style="animation-delay: ${index * 0.05}s">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2 flex-wrap">
                        ${match.sport === 'football' ? '<i class="fas fa-futbol text-green-400"></i>' : '<i class="fas fa-basketball-ball text-orange-400"></i>'}
                        <span class="text-gray-400 text-sm">${match.date} • ${match.time}</span>
                        ${match.is_today ? '<span class="bg-green-500/20 text-green-400 px-2 py-0.5 rounded text-xs font-medium">HOY</span>' : ''}
                        ${match.is_tomorrow ? '<span class="bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded text-xs font-medium">MAÑANA</span>' : ''}
                        ${match.league ? `<span class="bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded text-xs font-medium">${match.league}</span>` : ''}
                    </div>
                    ${Utils.getConfidenceBadge(match)}
                </div>

                <div class="flex items-center justify-between mb-4">
                    <div class="text-center flex-1">
                        <div class="font-semibold text-sm mb-1 truncate">${match.home_team}</div>
                        <div class="text-lg font-bold ${match.prediction_team === 'home' ? 'text-green-400' : 'text-gray-400'}">${match.home_odds}</div>
                    </div>
                    <div class="text-center px-3">
                        <div class="text-gray-600 text-xs font-bold">VS</div>
                    </div>
                    <div class="text-center flex-1">
                        <div class="font-semibold text-sm mb-1 truncate">${match.away_team}</div>
                        <div class="text-lg font-bold ${match.prediction_team === 'away' ? 'text-green-400' : 'text-gray-400'}">${match.away_odds}</div>
                    </div>
                </div>

                ${match.draw_odds ? `
                <div class="text-center mb-4 py-2 bg-white/5 rounded-lg">
                    <span class="text-gray-400 text-sm">Empate: </span>
                    <span class="font-bold ${match.prediction_team === 'draw' ? 'text-green-400' : 'text-gray-400'}">${match.draw_odds}</span>
                </div>
                ` : ''}

                <div class="border-t border-gray-700/30 pt-4">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-sm text-gray-400">Nivel de Confianza</span>
                        <span class="text-xl font-bold ${Utils.getConfidenceTextColor(match.confidence)}">${match.confidence}%</span>
                    </div>
                    <div class="h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div class="confidence-bar h-full bg-gradient-to-r ${Utils.getConfidenceColor(match.confidence)} rounded-full" style="width: ${match.confidence}%"></div>
                    </div>
                    <div class="mt-2 flex items-center justify-between">
                        <span class="text-sm text-gray-400">Pronóstico: </span>
                        <span class="font-medium ${Utils.getConfidenceTextColor(match.confidence)}">${match.prediction}</span>
                    </div>
                </div>
            </div>
        `).join('');
    },

    filterMatches(matches, filter) {
        switch (filter) {
            case 'today':
                return matches.filter(m => m.is_today);
            case 'tomorrow':
                return matches.filter(m => m.is_tomorrow);
            case 'football':
                return matches.filter(m => m.sport === 'football');
            case 'basketball':
                return matches.filter(m => m.sport === 'basketball');
            case 'favorites':
                return matches.filter(m => m.is_clear_favorite);
            case 'very-safe':
                return matches.filter(m => m.is_very_safe);
            case 'premier':
                return matches.filter(m => m.league === 'Premier League');
            case 'laliga':
                return matches.filter(m => m.league === 'La Liga');
            case 'seriea':
                return matches.filter(m => m.league === 'Serie A');
            case 'bundesliga':
                return matches.filter(m => m.league === 'Bundesliga');
            case 'ucl':
                return matches.filter(m => m.league === 'Champions League');
            case 'argentina':
                return matches.filter(m => m.league === 'Liga Argentina');
            default:
                return matches;
        }
    },

    updateFilterButtons(filter) {
        document.querySelectorAll('.filter-btn').forEach(btn => {
            if (btn.dataset.filter === filter) {
                btn.classList.remove('bg-white/10');
                btn.classList.add('bg-blue-600');
            } else {
                btn.classList.remove('bg-blue-600');
                btn.classList.add('bg-white/10');
            }
        });
    }
};

// Controlador
const App = {
    async init() {
        try {
            await this.loadData();
            this.scheduleNextUpdate();
        } catch (error) {
            console.error('Error initializing app:', error);
            Utils.showError('matches-container', 'Error al cargar los datos');
        }
    },

    async loadData() {
        Utils.showLoading('matches-container');
        Utils.showLoading('combinada-container');

        const [matchesData, combinadaData] = await Promise.all([
            API.getMatches(),
            API.getCombinada()
        ]);

        allMatches = matchesData.matches;
        Renderer.updateStats(matchesData.stats);
        Renderer.renderMatches();
        Renderer.renderCombinada(combinadaData.combinada);
    },

    filterMatches(filter) {
        currentFilter = filter;
        Renderer.updateFilterButtons(filter);
        Renderer.renderMatches();
    },

    refreshData() {
        Utils.showLoading('matches-container');
        Utils.showLoading('combinada-container');
        this.loadData();
    },

    scheduleNextUpdate() {
        const now = new Date();
        const argentinaTime = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + (3 * 3600000));
        const hours = argentinaTime.getHours();

        let nextUpdateHours;
        if (hours < 12) {
            nextUpdateHours = 12 - hours;
        } else {
            nextUpdateHours = 24 - hours;
        }

        const nextUpdateMinutes = 60 - argentinaTime.getMinutes();
        const nextUpdateMs = (nextUpdateHours * 60 * 60 * 1000) + (nextUpdateMinutes * 60 * 1000);

        console.log(`Próxima actualización a las ${new Date(now.getTime() + nextUpdateMs).toLocaleTimeString('es-AR', { timeZone: CONFIG.timeZone })} (hora argentina)`);

        setTimeout(() => {
            this.loadData();
            this.scheduleNextUpdate();
        }, nextUpdateMs);
    }
};

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// Funciones globales para HTML
window.filterMatches = (filter) => App.filterMatches(filter);
window.refreshData = () => App.refreshData();
