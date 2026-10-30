/* Only a complete, public stable release can enable a download action. */
'use strict';
const repository = 'Leaferd6712/Lead-the-Target';
const releaseEndpoint = `https://api.github.com/repos/${repository}/releases/latest`;
const suffixes = {source:'-source.zip',portable:'-windows-portable.zip',setup:'-windows-setup.exe'};

function presentRelease(release) {
  if (release.draft || release.prerelease || !/^v\d+\.\d+\.\d+$/.test(release.tag_name)) {
    throw new Error('No stable release');
  }
  const found = {};
  for (const [format,suffix] of Object.entries(suffixes)) {
    const name = `LeadTheTarget-${release.tag_name}${suffix}`;
    const asset = (release.assets || []).find(a => a.name===name && a.state==='uploaded' && a.size>0);
    if (!asset || !asset.browser_download_url.startsWith(`https://github.com/${repository}/releases/download/${release.tag_name}/`)) {
      throw new Error('Release is missing a verified distribution');
    }
    found[format] = asset;
  }
  for (const [format,asset] of Object.entries(found)) {
    const button = document.querySelector(`[data-format="${format}"]`);
    button.href = asset.browser_download_url;
    button.removeAttribute('aria-disabled'); button.removeAttribute('tabindex');
    document.querySelector(`[data-size="${format}"]`).textContent = `${(asset.size/1024/1024).toFixed(1)} MB`;
  }
  const date = new Date(release.published_at);
  const dateLabel = Number.isNaN(date.getTime()) ? '' : ` · ${date.toLocaleDateString(undefined,{year:'numeric',month:'long',day:'numeric'})}`;
  document.getElementById('release-status').textContent = `Latest stable: ${release.tag_name}${dateLabel}`;
  document.getElementById('checksum-link').href = release.html_url;
}

async function updateDownloads() {
  try {
    const response = await fetch(releaseEndpoint,{headers:{Accept:'application/vnd.github+json'},signal:AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error('Release service unavailable');
    presentRelease(await response.json());
  } catch (error) {
    // The deployment snapshot is a fallback for GitHub's anonymous API rate limit.
    try {
      const response = await fetch('release.json',{cache:'no-cache'});
      if (!response.ok) throw error;
      presentRelease(await response.json());
    } catch (_) {
      document.getElementById('release-status').textContent = 'Downloads unavailable here. Check the GitHub releases page for the latest build.';
    }
  }
}
updateDownloads();
