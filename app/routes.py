'''Module for website routing and rendering.

Maps the webpage URLs to specific functions which handle page logic and
rendering.

'''
from flask import render_template, flash, redirect, url_for, Response, request
from flask_login import login_required, login_user, logout_user, current_user
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

from datetime import datetime
import io
from statistics import stdev, mean, median
import os

from app import app, db, bcrypt, models, forms
from . import security


@app.route('/', methods=['GET', 'POST'])
def jobs():
    if not current_user.is_authenticated:
        form = forms.UserSignInForm()
        if form.validate_on_submit():
            user = models.User.get_by_email(form.email.data)
            if user is None or not bcrypt.check_password_hash(user.password, form.password.data):
                flash('Invalid email or password', 'danger')
                return redirect(url_for('jobs'))
            login_user(user)
            return redirect(url_for('jobs'))
        return render_template('base.html', form=form)
    else:
        page = request.args.get('page', 1, type=int)

        sort_by = current_user.settings.get_sort_by()
        if sort_by == 'id':
            jobs = models.PlugJob.query.order_by(models.PlugJob.id.desc())
        elif sort_by == 'name':
            jobs = models.PlugJob.query.join(models.PlugConfig).order_by(models.PlugConfig.name.desc())
        elif sort_by == 'status':
            jobs = models.PlugJob.query.order_by(models.PlugJob.status)
        elif sort_by == 'start_time':
            jobs = models.PlugJob.query.order_by(models.PlugJob.start_time.desc())
        elif sort_by == 'end_time':
            jobs = models.PlugJob.query.order_by(models.PlugJob.end_time.desc())
        elif sort_by == 'duration':
            jobs = models.PlugJob.query.order_by(models.PlugJob.duration.desc())

        sort_by = sort_by.replace('_', ' ')
        sort_by = ' '.join([word.capitalize() for word in sort_by.split(' ')])

        if current_user.settings.only_show_active:
            jobs = jobs.filter(models.PlugJob.query_is_active)

        jobs = jobs.paginate(page=page, per_page=10)
        configs = models.PlugConfig.query.order_by(models.PlugConfig.name)
        return render_template('pages/jobs.html', title='Jobs', page='jobs', configs=configs, jobs=jobs, sort_by=sort_by)


@app.route('/job/<int:job_id>', methods=['GET', 'POST'])
@login_required
def view_job(job_id):
    job = models.PlugJob.get_by_id(job_id)
    return render_template('pages/view_job.html', title=f'Job #{job.id}', page='jobs', job=job, config=job.config)


@app.route('/add-job-notes/<int:job_id>', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    job = models.PlugJob.get_by_id(job_id)
    form = forms.PlugJobForm()
    if form.validate_on_submit():
        job.notes = form.notes.data
        db.session.commit()
        flash(f'Updated {job.id}!', 'success')
        return redirect(url_for('jobs'))
    else:
        form.notes.data = job.notes
    return render_template('pages/edit_job.html', title=f'Edit Job #{job.id}', page='jobs', form=form, job=job, config=job.config)


@app.route('/start-job', methods=['GET', 'POST'])
@login_required
def start_job():
    config_id = request.form.get('config_select')
    config = models.PlugConfig.get_by_id(config_id)
    active_jobs = models.PlugJob.get_active()
    if active_jobs:
        flash(f'A job for {active_jobs[0].config.name} is active!', 'danger')
        return redirect(url_for('jobs'))
    job = models.PlugJob(config_id=config_id, start_time=datetime.now())
    job.save()
    flash(f'Started job for {config.name}!', 'success')
    return redirect(url_for('jobs'))


@app.route('/stop-job/<int:job_id>', methods=['GET', 'POST'])
@login_required
def stop_job(job_id):
    job = models.PlugJob.get_by_id(job_id)
    if not job.is_active():
        flash(f'Job for {job.config.name} already stopped!', 'danger')
        return redirect(url_for('jobs'))
    job.stop()
    flash(f'Stopped job for {job.config.name}!', 'success')
    return redirect(url_for('jobs'))


@app.route('/stop-all-jobs', methods=['GET', 'POST'])
@login_required
def stop_all_jobs():
    jobs = models.PlugJob.get_active()
    for job in jobs:
        job.stop()
    flash(f'Stopped all jobs!', 'success')
    return redirect(url_for('jobs'))


@app.route('/next-job-sort')
@login_required
def next_job_sort():
    def get_next_sort_by(sort_by):
        if sort_by == 'id':
            return 'name'
        elif sort_by == 'name':
            return 'status'
        elif sort_by == 'status':
            return 'start_time'
        elif sort_by == 'start_time':
            return 'end_time'
        elif sort_by == 'end_time':
            return 'duration'
        elif sort_by == 'duration':
            return 'id'

    sort_by = current_user.settings.get_sort_by()
    current_user.settings.sort_by = get_next_sort_by(sort_by)
    db.session.commit()
    return redirect(url_for('jobs'))


@app.route('/toggle-only-show-active')
@login_required
def toggle_only_show_active():
    current_user.settings.only_show_active = not current_user.settings.only_show_active
    db.session.commit()
    return redirect(url_for('jobs'))


@app.route('/configs', methods=['GET', 'POST'])
@login_required
def configs():
    page = request.args.get('page', 1, type=int)
    form = forms.PlugConfigForm()
    if form.validate_on_submit():
        config = create_config(form)
        config.save()
        flash(f'Added {config.name}!', 'success')
        return redirect(url_for('configs'))
    configs = models.PlugConfig.query_not_archived().paginate(page=page, per_page=5)
    return render_template('pages/configs.html', title='Configs', page='configs', form=form, configs=configs)


@app.route('/create-config/', methods=['GET', 'POST'])
@login_required
def create_config():
    form = forms.PlugConfigForm()
    if form.validate_on_submit():
        config = create_config(form)
        config.save()
        flash(f'Added {config.name}!', 'success')
        return redirect(url_for('configs'))
    return render_template('pages/create_config.html', title=f'Create Config', page='configs', form=form)


@app.route('/config/<int:config_id>', methods=['GET', 'POST'])
@login_required
def view_config(config_id):
    config = models.PlugConfig.get_by_id(config_id)
    return render_template('pages/view_config.html', title=f'{config.name}', page='configs', config=config)


@app.route('/edit-config/<int:config_id>', methods=['GET', 'POST'])
@login_required
def edit_config(config_id):
    config = models.PlugConfig.get_by_id(config_id)
    if config.is_archived:
        flash(f'Config {config.name} has been archived!', 'danger')
        return redirect(url_for('configs'))

    form = forms.PlugConfigForm()
    if form.validate_on_submit():
        if form.name.data != config.name:
            existing_config = models.PlugConfig.get_by_name(form.name.data)
            if existing_config:
                flash(f'Config with name {form.name.data} already exists!', 'danger')
                return redirect(url_for('edit_config', config_id=config_id))

        config.name = form.name.data
        config.cure_profile = form.cure_profile.data
        config.offset_x = form.offset_x.data
        config.offset_y = form.offset_y.data
        config.offset_z = form.offset_z.data
        config.vertical_gap_x = form.vertical_gap_x.data
        config.vertical_gap_y = form.vertical_gap_y.data
        config.vertical_gap_z = form.vertical_gap_z.data
        config.horizontal_gap_x = form.horizontal_gap_x.data
        config.horizontal_gap_y = form.horizontal_gap_y.data
        config.horizontal_gap_z = form.horizontal_gap_z.data
        config.slot_gap_x = form.slot_gap_x.data
        config.slot_gap_y = form.slot_gap_y.data
        config.slot_gap_z = form.slot_gap_z.data
        config.notes = form.notes.data
        db.session.commit()
        flash(f'Updated {config.name}!', 'success')
        return redirect(url_for('configs'))
    else:
        form.name.data = config.name
        form.cure_profile.data = config.cure_profile
        form.offset_x.data = config.offset_x
        form.offset_y.data = config.offset_y
        form.offset_z.data = config.offset_z
        form.vertical_gap_x.data = config.vertical_gap_x
        form.vertical_gap_y.data = config.vertical_gap_y
        form.vertical_gap_z.data = config.vertical_gap_z
        form.horizontal_gap_x.data = config.horizontal_gap_x
        form.horizontal_gap_y.data = config.horizontal_gap_y
        form.horizontal_gap_z.data = config.horizontal_gap_z
        form.slot_gap_x.data = config.slot_gap_x
        form.slot_gap_y.data = config.slot_gap_y
        form.slot_gap_z.data = config.slot_gap_z
        form.notes.data = config.notes
    return render_template('pages/edit_config.html', title=f'Edit {config.name}', page='configs', form=form, config=config)


@app.route('/copy-config/<int:config_id>', methods=['GET', 'POST'])
@login_required
def copy_config(config_id):
    config = models.PlugConfig.get_by_id(config_id)
    if models.PlugConfig.query.filter_by(name=f'{config.name} (copy)').first():
        flash(f'Copy of {config.name} already exists! Please rename it first.', 'danger')
        return redirect(url_for('configs'))

    new_config = models.PlugConfig(
        name=f'{config.name} (copy)',
        cure_profile=config.cure_profile,
        offset_x=config.offset_x,
        offset_y=config.offset_y,
        offset_z=config.offset_z,
        vertical_gap_x=config.vertical_gap_x,
        vertical_gap_y=config.vertical_gap_y,
        vertical_gap_z=config.vertical_gap_z,
        horizontal_gap_x=config.horizontal_gap_x,
        horizontal_gap_y=config.horizontal_gap_y,
        horizontal_gap_z=config.horizontal_gap_z,
        slot_gap_x=config.slot_gap_x,
        slot_gap_y=config.slot_gap_y,
        slot_gap_z=config.slot_gap_z,
        notes=config.notes
    )
    new_config.save()
    flash(f'Added {new_config.name}!', 'success')
    return redirect(url_for('configs'))


@app.route('/archive-config/<int:config_id>', methods=['GET', 'POST'])
@login_required
def archive_config(config_id):
    config = models.PlugConfig.get_by_id(config_id)
    config.archive()
    flash(f'Archived {config.name}!', 'success')
    return redirect(url_for('configs'))


@app.route('/insights')
@login_required
def insights():
    def calc_total_duration(jobs):
        return "{:.2f}".format(sum(job.duration for job in jobs if job.duration is not None))

    def calc_median_duration(jobs):
        durations = [job.duration for job in jobs if job.duration is not None]
        return "{:.2f}".format(median(durations) if durations else 0)

    def calc_mean_duration(jobs):
        durations = [job.duration for job in jobs if job.duration is not None]
        return "{:.2f}".format(mean(durations) if durations else 0)

    def calc_std_dev_duration(jobs):
        durations = [job.duration for job in jobs if job.duration is not None]
        return "{:.2f}".format(stdev(durations) if durations else 0)

    def calc_min_duration(jobs):
        return "{:.2f}".format(min(job.duration for job in jobs if job.duration is not None) if jobs else 0)

    def calc_max_duration(jobs):
        return "{:.2f}".format(max(job.duration for job in jobs if job.duration is not None) if jobs else 0)

    all = models.PlugJob.get_all()
    if len(all) < 5:
        return render_template('pages/insights.html', title='Insights', page='insights', analytics={'show': False})

    started = models.PlugJob.get_started()
    stopped = models.PlugJob.get_stopped()
    failed = models.PlugJob.get_failed()
    finished = models.PlugJob.get_finished()
    analytics = {
        'show': True,

        'started_jobs': len(started),
        'stopped_jobs': len(stopped),
        'failed_jobs': len(failed),
        'finished_jobs': len(finished),
        'all_jobs': len(all),

        'started_jobs_rate': 0,
        'stopped_jobs_rate': 0,
        'failed_jobs_rate': 0,
        'finished_jobs_rate': 0,

        'stopped_jobs_duration': "{:.2f}".format(float(calc_total_duration(stopped)) / 60),
        'failed_jobs_duration': "{:.2f}".format(float(calc_total_duration(failed)) / 60),
        'finished_jobs_duration': "{:.2f}".format(float(calc_total_duration(finished)) / 60),
        'all_jobs_duration': "{:.2f}".format(float(calc_total_duration(all)) / 60),

        'stopped_jobs_median': calc_median_duration(stopped),
        'failed_jobs_median': calc_median_duration(failed),
        'finished_jobs_median': calc_median_duration(finished),
        'all_jobs_median': calc_median_duration(all),

        'stopped_jobs_mean': calc_mean_duration(stopped),
        'failed_jobs_mean': calc_mean_duration(failed),
        'finished_jobs_mean': calc_mean_duration(finished),
        'all_jobs_mean': calc_mean_duration(all),

        'stopped_jobs_std_dev': calc_std_dev_duration(stopped),
        'failed_jobs_std_dev': calc_std_dev_duration(failed),
        'finished_jobs_std_dev': calc_std_dev_duration(finished),
        'all_jobs_std_dev': calc_std_dev_duration(all),

        'stopped_jobs_min': calc_min_duration(stopped),
        'failed_jobs_min': calc_min_duration(failed),
        'finished_jobs_min': calc_min_duration(finished),
        'all_jobs_min': calc_min_duration(all),

        'stopped_jobs_max': calc_max_duration(stopped),
        'failed_jobs_max': calc_max_duration(failed),
        'finished_jobs_max': calc_max_duration(finished),
        'all_jobs_max': calc_max_duration(all),
    }
    analytics['started_jobs_rate'] = "{:.2f}".format(analytics['started_jobs'] / analytics['all_jobs'] * 100)
    analytics['stopped_jobs_rate'] = "{:.2f}".format(analytics['stopped_jobs'] / analytics['all_jobs'] * 100)
    analytics['failed_jobs_rate'] = "{:.2f}".format(analytics['failed_jobs'] / analytics['all_jobs'] * 100)
    analytics['finished_jobs_rate'] = "{:.2f}".format(analytics['finished_jobs'] / analytics['all_jobs'] * 100)

    return render_template('pages/insights.html', title='Insights', page='insights', analytics=analytics)


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    email_form = forms.UserEmailForm()
    if email_form.validate_on_submit():
        current_user.email = email_form.email.data
        db.session.commit()
        flash('Your email was updated!', 'success')
        return redirect(url_for('account'))
    else:
        email_form.email.data = current_user.email

    password_form = forms.UserPasswordForm()
    if password_form.validate_on_submit():
        current_user.password = bcrypt.generate_password_hash(password_form.password.data).decode('utf-8')
        db.session.commit()
        flash('Your password was updated!', 'success')
        return redirect(url_for('account'))

    return render_template('pages/account.html', title='Account', page='account', email_form=email_form, password_form=password_form)


@app.route('/docs')
@login_required
def docs():
    app_url = os.environ.get('APP_URL', 'http://localhost:5000')
    return render_template('pages/docs.html', title='Docs', page='docs', app_url=app_url)


@app.route('/about')
@login_required
def about():
    return render_template('pages/about.html', title='About', page='about')


@app.route('/api/key', methods=['GET', 'POST'])
@login_required
def api_key():
    key = models.APIKey.query.filter_by(user_id=current_user.id).first()
    if key:
        key.delete()
    key = models.APIKey(name='', user_id=current_user.id)
    key.save()
    flash(f'Generated a new API key: {key.key}! Save this someplace safe!', 'success')
    return redirect(url_for('account'))


@app.route('/api/active', methods=['GET', 'POST'])
@security.api_key_required
def api_active():
    if request.method == 'POST':
        data = request.get_json(force=True)
        job = models.PlugJob.query.filter_by(id=data['id']).first()
        if job:
            if data['status'] == 'finished' or data['status'] == 'failed' or data['status'] == 'stopped':
                job.end()
                job.status = getattr(models.StatusEnum, data['status'])
                db.session.commit()
        return {'response': 200}, 200
    elif request.method == 'GET':
        active = [job.json() for job in models.PlugJob.get_active()]
        return {'response': 200, 'data': active}, 200


@app.route('/api/jobs', methods=['GET', 'POST'])
@security.api_key_required
def api_jobs():
    if request.method == 'GET':
        jobs = [job.json() for job in models.PlugJob.get_all()]
        return {'response': 200, 'data': jobs}, 200


@app.route('/api/configs', methods=['GET', 'POST'])
@security.api_key_required
def api_configs():
    if request.method == 'GET':
        configs = [config.json() for config in models.PlugConfig.get_all()]
        return {'response': 200, 'data': configs}, 200


@app.route('/durations-plot.png')
@login_required
def durations_plot():
    fig = create_durations_plot()
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')


@app.route('/status-plot.png')
@login_required
def status_plot():
    fig = create_status_plot()
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')


@app.route('/config-plot.png')
@login_required
def config_plot():
    fig = create_config_plot()
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out.', 'success')
    return redirect(url_for('jobs'))


def create_durations_plot():
    all = models.PlugJob.query.filter(models.PlugJob.duration.isnot(None)).order_by(models.PlugJob.end_time).limit(50).all()
    end_times = [job.end_time.strftime('%H:%M:%S') for job in all]
    durations = [job.duration for job in all]
    status = [job.status for job in all]

    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    axis.bar(end_times, durations)
    for i, s in enumerate(status):
        if s == models.StatusEnum.failed:
            axis.patches[i].set_facecolor('red')
        elif s == models.StatusEnum.stopped:
            axis.patches[i].set_facecolor('orange')
        elif s == models.StatusEnum.finished:
            axis.patches[i].set_facecolor('green')
    axis.set_title(f'Duration of Last {len(durations)} Completed Jobs')
    axis.set_xlabel('End Time')
    axis.set_ylabel('Duration (min)')
    fig.set_size_inches(10, 7.5)
    plt.setp(axis.get_xticklabels(), rotation=45, horizontalalignment='right')
    return fig


def create_status_plot():
    started = models.PlugJob.query.filter_by(status=models.StatusEnum.started).count()
    stopped = models.PlugJob.query.filter_by(status=models.StatusEnum.stopped).count()
    failed = models.PlugJob.query.filter_by(status=models.StatusEnum.failed).count()
    finished = models.PlugJob.query.filter_by(status=models.StatusEnum.finished).count()
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    axis.pie([started, stopped, failed, finished], labels=['Started', 'Stopped', 'Failed', 'Finished'], autopct='%1.1f%%')
    axis.patches[3].set_facecolor('#00FF00')
    axis.patches[2].set_facecolor('#FF0000')
    axis.patches[1].set_facecolor('#FFFF00')
    axis.patches[0].set_facecolor('#0000FF')
    axis.set_title('Status of Jobs')
    fig.set_size_inches(5, 4)
    fig.subplots_adjust(left=0, right=1, top=0.93, bottom=0.1)
    return fig


def create_config_plot():
    config_counts = {}
    for config in models.PlugConfig.get_all():
        config_counts[config.name] = len(models.PlugJob.query.filter_by(config_id=config.id).all())
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    axis.pie(config_counts.values(), labels=config_counts.keys(), autopct='%1.1f%%')
    axis.set_title('Jobs by Configuration')
    fig.set_size_inches(5, 4)
    fig.subplots_adjust(left=0, right=1, top=0.93, bottom=0.1)
    return fig


def create_config(form):
    return models.PlugConfig(
        name=form.name.data,
        cure_profile=form.cure_profile.data,
        offset_x=form.offset_x.data,
        offset_y=form.offset_y.data,
        offset_z=form.offset_z.data,
        vertical_gap_x=form.vertical_gap_x.data,
        vertical_gap_y=form.vertical_gap_y.data,
        vertical_gap_z=form.vertical_gap_z.data,
        horizontal_gap_x=form.horizontal_gap_x.data,
        horizontal_gap_y=form.horizontal_gap_y.data,
        horizontal_gap_z=form.horizontal_gap_z.data,
        slot_gap_x=form.slot_gap_x.data,
        slot_gap_y=form.slot_gap_y.data,
        slot_gap_z=form.slot_gap_z.data,
        notes=form.notes.data
    )
