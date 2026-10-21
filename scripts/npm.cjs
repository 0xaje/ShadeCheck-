// Cross-platform convenience launcher. Python remains the product runtime.
const {spawnSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path');
const windows=process.platform==='win32';
const candidates=[path.resolve(windows?'.venv/Scripts/python.exe':'.venv/bin/python'),windows?'py':'python3'];
const mode=process.argv[2];
const commands={dev:['-m','shadecheck.cli','dashboard'],demo:['-m','shadecheck.cli','demo'],test:['-m','unittest','discover','-s','tests','-v']};
if(!commands[mode]){console.error('Choose dev, demo or test.');process.exit(2);}
for(const command of candidates){if(command.includes(path.sep)&&!fs.existsSync(command))continue;const args=[...(command==='py'?['-3']:[]),...commands[mode],...process.argv.slice(3)];const r=spawnSync(command,args,{stdio:'inherit',shell:false});if(r.error?.code==='ENOENT')continue;process.exit(r.status??2);}
console.error('Python was not found. Create .venv and install ShadeCheck.');process.exit(2);
