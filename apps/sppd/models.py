from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from api.models import TimeStampedUUIDModel

# Create your models here.
class ActiveRole(models.Model):
    ACTIVE_ROLE = (
        ('ppk', 'PPK'),
        ('kpa', 'KPA'),
        ('operator', 'Operator'),
        ('employee', 'Employee')
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="active_role") 
    active_role = models.CharField(max_length=255, null=True, blank=True, choices=ACTIVE_ROLE)

    def __str__(self):
        return self.user.username

class Issuer(TimeStampedUUIDModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="issuer_user", blank=True, null=True)

class Province(TimeStampedUUIDModel):
    code = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

class Destination(TimeStampedUUIDModel):
    code = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    province = models.ForeignKey(Province, on_delete=models.CASCADE, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

class TravelPurpose(TimeStampedUUIDModel):
    name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

class Transportation(TimeStampedUUIDModel):
    code = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    via = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name
    
class BudgetAccount(TimeStampedUUIDModel):
    code = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

class SBMMaster(TimeStampedUUIDModel):
    grade = models.CharField(max_length=1, unique=True)  # A, B, C, D
    description = models.CharField(max_length=255, blank=True)
    lodging_limit = models.DecimalField(max_digits=14, decimal_places=0)  # batas penginapan per malam
    representation_allowance = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)  # hanya terisi untuk tingkat A

    def __str__(self):
        return self.grade

class DailyAllowanceRate(TimeStampedUUIDModel):
    province = models.ForeignKey(Province, on_delete=models.CASCADE, blank=True, null=True)
    amount = models.DecimalField(max_digits=14, decimal_places=0)

    def __str__(self):
        return self.province

class Document(TimeStampedUUIDModel):
    STATE = (
        ('sppd_draft', 'SPPD Draft'), 
        ('verification', 'Verification'), # Operator: Dokumen sppd diajukan
        ('waiting_ppk', 'Waiting PPK'), # PPK: dokumen sppd diperiksa & diverifikasi
        ('waiting_kpa', 'Waiting KPA'), # KPA: dokumen sppd diperiksa & disahkan
        ('approved', 'Approved'), # Pegawai : dokumen sppd disahkan & dapat dicetak
        ('draft_spj', 'SPJ Draft'), # Pegawai: dokumen spj diajukan
        ('spj_verification', 'SPJ Verification'),  # Operator: laporan & bukti diperiksa
        ('spj_ratification', 'SPJ Ratification'),  # PPK: pengesahan & penetapan selisih
        ('spj_revision', 'SPJ Revision'),  # Pegawai: unggah ulang setelah catatan perbaikan
        ('rejected', 'Rejected'),  # Document rejected by approver
        ('waiting_for_cancelation', 'Waiting For Cancellation'),  # PPK: menunggu pengesahan penolakan
        ('cancelled', 'Cancelled'), 
        ('complete', 'Done'),
        ('revision', 'Revision'),
    )

    SUBMISSION_TYPE = (
        ('lumpsum', 'Lumpsum'),
        ('reimburse', 'Reimburse'),
        ('dp', 'DP'),
    )
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="creator", blank=True, null=True) # yg membuat
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="employee", blank=True, null=True) # yg ditugaskan
    current = models.IntegerField(null=True, blank=True)
    authors = models.ForeignKey(User, on_delete=models.CASCADE, related_name="authors", blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True, choices=STATE)
    subject = models.TextField(blank=True, null=True)
    readers = models.ManyToManyField(User, related_name="readers", blank=True) # yg bisa membaca dokumen
    travel_purpose = models.ForeignKey(TravelPurpose, on_delete=models.CASCADE, blank=True, null=True) # maksud perjalanan dinas
    assignment_basis = models.CharField(max_length=255, blank=True, null=True)
    departure_date = models.DateTimeField(editable=True) # tanggal keberangkatan
    transportation_type = models.ForeignKey(Transportation, on_delete=models.CASCADE, blank=True, null=True)
    cost_category = models.ForeignKey(SBMMaster, on_delete=models.CASCADE, blank=True, null=True) # tingkat biaya perjalanan
    issuer = models.ForeignKey(Issuer, on_delete=models.CASCADE, blank=True, null=True) # pejabat pemberi perintah perjalanan dinas
    submission_type = models.CharField(max_length=255, blank=True, null=True, choices=SUBMISSION_TYPE) # Jenis / Mekanisme Pengajuan
    dp = models.IntegerField(blank=True, null=True) # Persen DP
    total_allowance = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    budget_account = models.ForeignKey(BudgetAccount, on_delete=models.CASCADE, blank=True, null=True) # mata anggaran
    program_output_code = models.CharField(max_length=255, blank=True, null=True) # kode program/output
    file = models.FileField(upload_to="sppd/file/", null=True, blank=True)
    file_issuer = models.FileField(upload_to="sppd/file_issuer/", null=True, blank=True)

    def __str__(self):
        return self.assignment_basis

    @property
    def get_next_approver(self):
        approvers_count = self.approver_document.filter(is_delete=False).count()
        current = self.current
        if current + 1 >= approvers_count:
            return self.approver_document.get(sequence=(approvers_count - 1))
        else:
            return self.approver_document.get(sequence=(current + 1))

    @property
    def get_prev_approver(self):
        current = self.current
        if current - 1 < 0:
            return self.approver_document.get(sequence=(current - 1))
        else:
            return self.approver_document.get(sequence=((current - 1) - 1))

    @property
    def get_current_approver(self):
        approvers_count = self.approver_document.filter(is_delete=False).count()
        current = self.current
        if current + 1 >= approvers_count:
            return self.approver_document.get(sequence=(approvers_count - 1))
        else:
            return self.approver_document.get(sequence=current)

    def get_approvers_list(self, role=None, type=None):
        if type:
            return self.approver_document.filter(type=type, is_delete=False).order_by('sequence').all()
        elif role:
            return self.approver_document.filter(role=role, is_delete=False).order_by('sequence').all()
        elif role and type:
            return self.approver_document.filter(role=role, type=type, is_delete=False).order_by('sequence').all()
        else:
            return self.approver_document.filter(is_delete=False).order_by('sequence').all()

    def set_document_state(self, declined=False, cancel=False, revision=False):
        if self.current == 0 and not declined and not cancel and not revision:
            self.state = 'sppd_draft'
        else:
            if declined:
                if self.get_current_approver.role in ['operator', 'kpa', 'ppk'] and declined:
                    if self.spj.count() > 0:
                        self.state = 'spj_revision'
                    else:
                        self.state = 'rejected'
            elif cancel:
                if self.get_current_approver.role == 'ppk' and cancel:
                    self.state = 'waiting_for_cancelation'
                elif self.get_current_approver.role == 'kpa' and cancel:
                    self.state = 'cancelled'
                elif self.get_current_approver.role == 'employee' and cancel:
                    self.state = 'cancelled'
            elif revision:
                if self.get_current_approver.role in ['operator', 'employee'] and revision:
                    if self.spj.count() > 0:
                        self.state = 'spj_revision'
                    else:
                        self.state = 'revision'
            else:
                if self.get_current_approver.role == 'operator':
                    if self.spj.count() > 0:
                        self.state = 'spj_verification'
                    else:
                        self.state = 'verification'
                elif self.get_current_approver.role == 'ppk':
                    if self.spj.count() > 0:
                        self.state = 'spj_ratification'
                    else:
                        self.state = 'waiting_ppk'
                elif self.get_current_approver.role == 'kpa':
                    self.state = 'waiting_kpa'
                elif self.get_current_approver.role == 'employee':
                    if self.spj.count() > 0:
                        self.state = 'complete'
                    else:
                        self.state = 'approved'
        self.save()

    @property
    def get_issuer_display(self):
        if self.issuer:
            return f"{self.issuer.user.profile_set.first().name}"
        else:
            return None

    @property
    def return_date(self):
        total_days = sum(self.travel_assignment.filter(is_delete=False).values_list('duration_days', flat=True))

        return self.departure_date + timedelta(days=total_days - 1)

    @property
    def destination_cities(self):
        return ", ".join(
            self.travel_assignment.exclude(destination_city__isnull=True, is_delete=False).exclude(destination_city='').values_list('destination_city', flat=True)
        )

class TravelAssignment(TimeStampedUUIDModel):
    origin_city = models.CharField(max_length=255, blank=True, null=True)
    destination_city = models.CharField(max_length=255, blank=True, null=True)
    duration_days = models.IntegerField(null=True, blank=True)
    persons = models.IntegerField(null=True, blank=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="travel_assignment", blank=True, null=True)
    daily_allowance = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    accommodation_allowance = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    lodging_allowance = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    sub_total_allowance = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)

    def __str__(self):
        return f"{self.origin_city} - {self.destination_city}"
    
class Approver(TimeStampedUUIDModel):
    ROLE = (
        ('ppk', 'PPK'),
        ('kpa', 'KPA'),
        ('operator', 'Operator'),
        ('issuer', 'Issuer'),
        ('employee', 'Employee')
    )

    TYPE = (
        ('sppd', 'SPPD'),
        ('spj', 'SPJ'),
    )

    ACTION = (
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('return', 'Return'),
        ('cancel', 'Cancel'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="approver", blank=True, null=True)
    role = models.CharField(max_length=255, blank=True, null=True, choices=ROLE)
    type = models.CharField(max_length=255, blank=True, null=True, choices=TYPE)
    action = models.CharField(max_length=255, blank=True, null=True, choices=ACTION)
    sequence = models.IntegerField(null=True, blank=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="approver_document", blank=True, null=True)
    flag = models.CharField(max_length=255, blank=True, null=True)

class SPJ(TimeStampedUUIDModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="spj", blank=True, null=True)
    departure_date = models.DateTimeField()
    return_date = models.DateTimeField()
    summary_activity = models.TextField(null=True, blank=True)
    recommendation = models.TextField(null=True, blank=True)
    report_activity = models.FileField(upload_to="sppd/reports/activity/", null=True, blank=True)
    sppd_signed = models.FileField(upload_to="sppd/reports/signed/", null=True, blank=True)
    ticket_and_boarding_pass = models.FileField(upload_to="sppd/reports/tickets/", null=True, blank=True)
    accommodation_invoice = models.FileField(upload_to="sppd/reports/accommodation-invoices/", null=True, blank=True)
    evidence_local_transport = models.FileField(upload_to="sppd/reports/local-transport/", null=True, blank=True)
    documentation_activity = models.FileField(upload_to="sppd/reports/documentation/", null=True, blank=True)
    file = models.FileField(upload_to="sppd/reports/file/", null=True, blank=True)
    daily_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    accommodation_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    lodging_allowance = models.DecimalField(max_digits=15,decimal_places=2,default=0)
    local_lodging = models.DecimalField(max_digits=15,decimal_places=2,default=0)
    total_allowance = models.DecimalField(max_digits=15,decimal_places=2,default=0)
    underpayment = models.DecimalField(max_digits=15,decimal_places=2,default=0)
    overpayment = models.DecimalField(max_digits=15,decimal_places=2,default=0)

    def __str__(self):
        return self.document.assignment_basis

class PaguSPPD(TimeStampedUUIDModel):
    working_unit_id = models.CharField(max_length=255, blank=True, null=True)
    working_unit_name = models.CharField(max_length=255, blank=True, null=True)
    working_unit_code = models.CharField(max_length=255, blank=True, null=True)
    working_unit_level = models.CharField(max_length=255, blank=True, null=True)
    pagu = models.DecimalField(max_digits=30,decimal_places=2,default=0)

    def __str__(self):
        return self.pagu