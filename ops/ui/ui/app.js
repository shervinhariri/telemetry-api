// Minimal client logic for NETREEX UI to wire TASKS and tabs
(function(){
  function byId(id){ return document.getElementById(id); }
  function showPanel(id){
    const panels = ['panel-dashboard','panel-sources','panel-requests','panel-toolbox','panel-logs'];
    panels.forEach(pid => {
      const el = byId(pid);
      if (!el) return;
      if (pid === id) el.classList.remove('hidden'); else el.classList.add('hidden');
    });
  }

  function init(){
    const btnTasks = byId('btn-open-tasks');
    if (btnTasks){
      btnTasks.addEventListener('click', function(){ showPanel('panel-toolbox'); });
    }

    const tabMap = {
      'tab-dashboard': 'panel-dashboard',
      'tab-sources': 'panel-sources',
      'tab-requests': 'panel-requests',
      'tab-toolbox': 'panel-toolbox',
      'tab-logs': 'panel-logs'
    };
    Object.keys(tabMap).forEach(tabId => {
      const btn = byId(tabId);
      if (btn){ btn.addEventListener('click', () => showPanel(tabMap[tabId])); }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();


